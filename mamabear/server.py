#!/usr/bin/env python

import os
import cherrypy
import ConfigParser

from mamabear.controllers import *
from mamabear.plugin import SAEnginePlugin, SATool

HERE = os.path.dirname(os.path.abspath(__file__))

def cors():
    cherrypy.response.headers["Access-Control-Request-Method"] = "*"
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
    cherrypy.response.headers["Access-Control-Allow-Headers"] = "Origin, Accept, Authorization, Content-Type, X-Requested-With, x-csrf-token"
    cherrypy.response.headers["Access-Control-Allow-Credentials"] = "true"
    cherrypy.response.headers["Access-Control-Allow-Methods"] = "POST,GET,OPTIONS,DELETE,PUT"
    cherrypy.response.headers["Access-Control-Max-Age"] = "86400"
    
def get_app():
    d = cherrypy.dispatch.RoutesDispatcher()
    d.connect(name='mamabear-hosts', route="/mamabear", controller=HostController)
    d.connect(name='mamabear-apps', route="/mamabear", controller=AppController)

    with d.mapper.submapper(path_prefix='/mamabear/v1', controller='mamabear-hosts') as m:
        m.connect('hosts', '/host', action='list_hosts')

    with d.mapper.submapper(path_prefix='/mamabear/v1', controller='mamabear-apps') as m:
        m.connect('apps', '/app', action='list_apps', conditions=dict(method=['GET']))
        m.connect('images', '/app/{name}/images', action='app_images', conditions=dict(method=['GET']))
        m.connect('deployments', '/app/{name}/deployments', action='app_deployments', conditions=dict(method=['GET']))
            
    server_cfg = {
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 9055,
        'tools.cors.on': True,
        'tools.gzip.on': True,
        'tools.gzip.mime_types': ["application/json"],
        'tools.db.on': True,
        'tools.staticdir.root': HERE+'/../'
    }

    cherrypy.config.update(server_cfg)

    config = {
        '/': {
            'request.dispatch': d
        },
        '/web': {
            'tools.staticdir.dir': 'static',
            'tools.staticdir.on': True,
            'tools.staticdir.index': 'index.html'            
        },
    }

    cherrypy.engine.autoreload.unsubscribe()
    app = cherrypy.tree.mount(root=None, config=config)
    return app

    
def start():
    config = ConfigParser.ConfigParser()
    
    env = os.environ.get('CLICK2CARE_ENVIRONMENT')
    if env:
        config.readfp(open(HERE+'/../conf/mamabear.'+env+'.cfg'))
    else:
        config.readfp(open(HERE+'/../conf/mamabear.cfg'))
        
    app = get_app()

    connection_string = "mysql://%s:%s@%s/%s" % (
        config.get('mysql', 'user'),
        config.get('mysql', 'passwd'),
        config.get('mysql', 'host'),
        config.get('mysql', 'database')
    )

    SAEnginePlugin(cherrypy.engine, connection_string).subscribe()
    cherrypy.tools.db = SATool()
    cherrypy.tools.cors = cherrypy.Tool('before_handler', cors)
    
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.quickstart(app)

if __name__ == '__main__':
    start()
