import cherrypy
from mamabear.model import *

class HostController(object):

    @cherrypy.tools.json_out()
    def list_hosts(self, hostname=None, type=None):
        if hostname:
            return {
                'hits': [self.get_host(hostname=hostname)],
                'total': 1
            }
            
        return {
            'hits': Host.list(cherrypy.request.db, type=type),
            'total': Host.count(cherrypy.request.db, type=type)
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
            
        
class AppController(object):

    apps = [
        {
            'name': 'sagebear',
            'images': [
                {'tag':'1', 'hash':'sagebear-image-0'},
                {'tag':'2', 'hash':'sagebear-image-1'}
            ],
            'deployments': {
                'test': {
                    'configuration': {
                        'image': '1',
                        'status_endpoint': '/status',
                        'mapped_ports': [
                            '9041:9041'
                        ],
                        'hosts': [
                            '10.0.0.1',
                            '10.0.0.3'
                        ]
                    },
                    'containers': [
                        {'host':'10.0.0.1', 'container': 'sagebear-1-instance0', 'status': 'ok'},
                        {'host':'10.0.0.3', 'container': 'sagebear-1-instance1', 'status': 'ok'}
                    ]
                }
            }
        },
        {
            'name': 'carebear',
            'images': [
                {'tag':'1', 'hash':'cb-image-1'},
                {'tag':'2', 'hash':'cb-image-2'},
                {'tag':'3', 'hash':'cb-image-3'}
            ],
            'deployments': {
                'test': {
                    'configuration': {
                        'image': '3',
                        'status_endpoint': '/carebear/status',
                        'mapped_ports': [
                            '9001:9001'
                        ],
                        'hosts': [
                            '10.0.0.1',
                            '10.0.0.2',
                            '10.0.0.3'
                        ]
                    },
                    'containers': [
                        {'host':'10.0.0.1', 'container': 'carebear-3-instance0', 'status': 'ok'},
                        {'host':'10.0.0.2', 'container': 'carebear-3-instance2', 'status': 'ok'},
                        {'host':'10.0.0.3', 'container': 'carebear-3-instance3', 'status': 'error'}
                    ]
                },
                'prod': {
                    'configuration': {
                        'image': '2',
                        'status_endpoint': '/carebear/status',
                        'mapped_ports': [
                            '9001:9001'
                        ],
                        'hosts': [
                            '10.0.0.1',
                            '10.0.0.2',
                            '10.0.0.3'
                        ]
                    },
                    'containers': [
                        {'host':'10.0.0.1', 'container': 'carebear-2-instance0', 'status': 'ok'},
                        {'host':'10.0.0.2', 'container': 'carebear-2-instance2', 'status': 'ok'},
                        {'host':'10.0.0.3', 'container': 'carebear-2-instance3', 'status': 'ok'}
                    ]
                }
            }
            
        },
        {
            'name': 'curator',
            'images': [
                {'tag':'1', 'hash':'cur-image-2'}
            ]                
        }
    ]
    
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
