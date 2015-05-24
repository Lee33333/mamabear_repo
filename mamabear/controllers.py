import cherrypy
from mamabear.model import *

class HostController(object):

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
                cherrypy.response.status = 201
                return {'created':"({}:{},{})".format(deployment.app_name, deployment.image_tag, deployment.environment)}
            else:
                cherrypy.response.status = 500
                return {'error': 'internal server error'}
                
        cherrypy.response.status = 400
        return {'error': 'malformed request, request body must include deployment data with {}'.format(Deployment.required_keys)}
