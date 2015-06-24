import cherrypy
from mamabear.model import *

class HostController(object):

    #
    # FIXME - need to do a full fledged list with filters and
    # sorting now that we have more fields.
    #
    @cherrypy.tools.json_out()
    def list_hosts(self, hostname=None):
        if hostname:
            return {
                'hits': [self.get_host(hostname=hostname)],
                'total': 1
            }
            
        return {
            'hits': Host.list(cherrypy.request.db),
            'total': Host.count(cherrypy.request.db)
        }
        
    def get_host(self, hostname=None):
        if not hostname:
            cherrypy.response.status = 400
            return {"error":"no hostname specified"}
            
        host = Host.get_by_name(cherrypy.request.db, hostname=hostname)
        if host:
            return host.encode()

        cherrypy.response.status = 404
        return {"error":"host with name {0} not found".format(hostname)}

    @cherrypy.tools.json_out()
    def delete_host(self, alias):            
        deleted = Host.delete_by_alias(cherrypy.request.db, alias)
        return {"deleted":deleted, "name":alias}
        
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def add_host(self):
        data = cherrypy.request.json
        if 'host' in data and 'hostname' in data['host']:
            host = Host.get_by_name(cherrypy.request.db, data['host']['hostname'])
            if host:
                cherrypy.response.status = 409
                return {'error': 'Host with name {} already exists'.format(data['host']['hostname'])}

            if 'asg_name' in data['host']:
                group = AWSAutoScalingGroup.get(cherrypy.request.db, data['host']['asg_name'])
                if not group:
                    cherrypy.response.status = 409
                    return {'error': 'ASG with name {} does not exist'.format(data['host']['asg_name'])}
                    
            host = Host.create(cherrypy.request.db, data['host'])
            if host:
                try:
                    self.worker.update_host_containers(cherrypy.request.db, host, self.worker._config)
                except Exception as e:
                    cherrypy.log.error("Can't update host containers", traceback=True)
                    return {'warn': "Host unreachable"}
                    
                cherrypy.response.status = 201
                return {'created':host.hostname}
            else:
                cherrypy.response.status = 500
                return {'error': 'internal server error'}
                
        cherrypy.response.status = 400
        return {'error': 'malformed request, request body must include host data'}
        
class AppController(object):

    @cherrypy.tools.json_out()
    def list_apps(self, name=None):
        return {'hits': App.list(cherrypy.request.db, name=name),
                'total': App.count(cherrypy.request.db, name=name)}        

    @cherrypy.tools.json_out()
    def delete_app(self, name):
        deleted = App.delete(cherrypy.request.db, name)    
        return {"deleted":deleted, "name": name}
        
    @cherrypy.tools.json_out()
    def app_images(self, name):
        app = App.get(cherrypy.request.db, name)
        if app:
            return {
                name: {
                    'images': [image.encode() for image in app.images]
                }
            }

        cherrypy.response.status = 404
        return {"error":"app with name {0} not found".format(name)}

    @cherrypy.tools.json_out()
    def app_deployments(self, name):
        app = App.get(cherrypy.request.db, name)
        if app:
            return {
                name: {
                    'deployments': [dep.encode() for dep in app.deployments]
                }
            }

        cherrypy.response.status = 404
        return {"error":"app with name {0} not found".format(name)}

    @cherrypy.tools.json_out()
    def refresh_images(self, name):
        app = App.get(cherrypy.request.db, name)
        try:
            self.worker.update_app_images(cherrypy.request.db, app)
        except Exception as e:
            cherrypy.log.error("Can't refresh images", traceback=True)
            cherrypy.response.status = 500
            return {'error': e.message} 
        return app.encode()    


    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def add_app(self):
        data = cherrypy.request.json
        if 'app' in data and 'name' in data['app']:
            app = App.get(cherrypy.request.db, data['app']['name'])
            if app:
                cherrypy.response.status = 409
                return {'error': 'App with name {} already exists'.format(data['app']['name'])}
                    
            app = App.create(cherrypy.request.db, data['app']['name'])
            if app:
                try:
                    self.worker.update_app_images(cherrypy.request.db, app)
                except Exception as e:
                    cherrypy.log.error("Can't update images", traceback=True)
                    return {'warn': "No images for app in registry"}
                    
                cherrypy.response.status = 201
                return {'created':app.name}
            else:
                cherrypy.response.status = 500
                return {'error': 'internal server error'}
                
        cherrypy.response.status = 400
        return {'error': 'malformed request, request body must include app data'}

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def add_app_deployment(self, name=None):
        data = cherrypy.request.json
        if 'deployment' in data and all(k in data['deployment'] for k in Deployment.required_keys):
            d = data['deployment']
            app = d['app_name']
            image = d['image_tag']
            env = d['environment']
            deployment = Deployment.get_by_app(cherrypy.request.db, app, image_tag=image, environment=env)
            if deployment:
                cherrypy.response.status = 409
                return {'error': 'Deployment with configuration ({}:{},{}) already exists'.format(app, image, env)}
                    
            deployment = Deployment.create(cherrypy.request.db, d)
            if deployment:
                try:
                    self.worker.update_app_images(cherrypy.request.db, App.get(cherrypy.request.db, app))
                    self.worker.update_deployment
                    (cherrypy.request.db, deployment)
                except Exception as e:
                    cherrypy.log.error("Failed updating images and running containers", traceback=True)
                    return {'warn': "Failed updating images and running containers"}
                    
                cherrypy.response.status = 201
                return {'created':"({}:{},{})".format(deployment.app_name, deployment.image_tag, deployment.environment)}
            else:
                cherrypy.response.status = 500
                return {'error': 'internal server error'}
                
        cherrypy.response.status = 400
        return {'error': 'malformed request, request body must include deployment data with {}'.format(Deployment.required_keys)}

class DeploymentController(object):

    @cherrypy.tools.json_out()
    def get_deployment(self, app_name, image_tag, environment):
        deployment = Deployment.get_by_app(cherrypy.request.db, app_name, image_tag=image_tag, environment=environment)
        if deployment:
            return deployment.encode()
        cherrypy.response.status = 404
        return {'error': 'deployment configuration ({}:{},{}) not found'.format(app_name, image_tag, environment)}
        
    @cherrypy.tools.json_out()
    def list_deployments(self, app_name=None, image_tag=None, environment=None,
                         order='asc', sort_field='app_name', limit=10, offset=0):
        return {
            'hits': Deployment.list(cherrypy.request.db, app_name=app_name, image_tag=image_tag, environment=environment,
                                    order=order, sort_field=sort_field, limit=limit, offset=offset),
            'total': Deployment.count(cherrypy.request.db, app_name=app_name, image_tag=image_tag, environment=environment)
        }

    @cherrypy.tools.json_out()
    def delete_deployment(self, app_name, image_tag, environment):
        deleted = Deployment.delete(cherrypy.request.db, app_name, image_tag, environment)
        return {'deleted': deleted, 'deployment':'{}:{}/{}'.format(app_name, image_tag, environment)}
        
    @cherrypy.tools.json_out()
    def run_deployment(self, app_name, image_tag, environment):
        deployment = Deployment.get_by_app(cherrypy.request.db, app_name, image_tag=image_tag, environment=environment)
        if deployment:
            self.worker.run_deployment(deployment.id)            
            return deployment.encode()
            
        cherrypy.response.status = 404
        return {'error': 'deployment configuration ({}:{},{}) not found'.format(app_name, image_tag, environment)}

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def update_deployment(self, app_name, image_tag, environment):
        data = cherrypy.request.json
        if 'deployment' in data:
            updated = Deployment.update_by_app(cherrypy.request.db, app_name, image_tag, environment, data['deployment'])
            return {'updated':updated, 'deployment': '{}:{}/{}'.format(app_name, image_tag, environment)}
                
        cherrypy.response.status = 400        
        return {'error': 'malformed request, body must include deployment data'}
        
class ImageController(object):

    @cherrypy.tools.json_out()
    def list_images(self, app_name=None, image_tag=None, order='asc', sort_field='app_name', limit=10, offset=0):
        return {
            'hits': Image.list(cherrypy.request.db, app_name=app_name, image_tag=image_tag, order=order,
                               sort_field=sort_field, limit=limit, offset=offset),
            'total': Image.count(cherrypy.request.db, app_name=app_name, image_tag=image_tag)
        }
