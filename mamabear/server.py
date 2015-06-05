#!/usr/bin/env python

import os
import sys
import json
import getopt
import cherrypy
import ConfigParser
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from mamabear.worker import Worker
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
    d.connect(name='mamabear-deployments', route='/mamabear', controller=DeploymentController)
    d.connect(name='mamabear-images', route='/mamabear', controller=ImageController)
    
    with d.mapper.submapper(path_prefix='/mamabear/v1', controller='mamabear-hosts') as m:
        m.connect('hosts', '/host', action='list_hosts', conditions=dict(method=['GET']))
        m.connect('hosts_new', '/host', action='add_host', conditions=dict(method=['POST']))
        m.connect('hosts_delete', '/host/{hostname}', action='delete_host', conditions=dict(method=['DELETE']))

    with d.mapper.submapper(path_prefix='/mamabear/v1', controller='mamabear-images') as m:
        m.connect('images', '/image', action='list_images', conditions=dict(method=['GET']))

    with d.mapper.submapper(path_prefix='/mamabear/v1', controller='mamabear-deployments') as m:
        m.connect('deployments_all', '/deployment', action='list_deployments', conditions=dict(method=['GET']))
        m.connect('deployment', '/deployment/{app_name}/{image_tag}/{environment}', action='get_deployment', conditions=dict(method=['GET']))
        m.connect('run_deployment', '/deployment/{app_name}/{image_tag}/{environment}/run', action='run_deployment')
        m.connect('delete_deployment', '/deployment/{app_name}/{image_tag}/{environment}', action='delete_deployment', conditions=dict(method=['DELETE']))

    with d.mapper.submapper(path_prefix='/mamabear/v1', controller='mamabear-apps') as m:
        m.connect('apps', '/app', action='list_apps', conditions=dict(method=['GET']))
        m.connect('apps_new', '/app', action='add_app', conditions=dict(method=['POST']))
        m.connect('images', '/app/{name}/images', action='app_images', conditions=dict(method=['GET']))
        m.connect('deployments', '/app/{name}/deployments', action='app_deployments', conditions=dict(method=['GET']))
        m.connect('deployments_new', '/app/{name}/deployments', action='add_app_deployment', conditions=dict(method=['POST']))
        m.connect('deployment_hosts', '/app/{name}/deployments/{image_tag}/{environment}', action='add_deployment_hosts', conditions=dict(method=['PUT']))
        
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

    
def start(config):
    app = get_app()

    AppController.worker = Worker(config)
    HostController.worker = Worker(config)
    DeploymentController.worker = Worker(config)
    
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

def update_all_job(config):
    worker = Worker(config)
    worker.update_all()
    
def start_worker(config):
    connection_string = "mysql://%s:%s@%s/%s" % (
        config.get('mysql', 'user'),
        config.get('mysql', 'passwd'),
        config.get('mysql', 'host'),
        config.get('mysql', 'database')
    )
    
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(SQLAlchemyJobStore(url=connection_string), alias='db')
    scheduler.start()
    scheduler.add_job(
        update_all_job, args=[config], replace_existing=True, id='worker',
        trigger='cron', minute='*/5', jobstore='db', timezone='UTC')
    
if __name__ == '__main__':
    argv = sys.argv[1:]
    conf = None

    try:
        opts, args = getopt.getopt(argv, "hc:")
    except getopt.GetoptError:
        print 'Usage: server.py -c <configFile>'
        sys.exit(2)

    for opt, arg in opts:
        if opt == "-h":
            print 'Usage: server.py -c <configFile>'
        elif opt == "-c":
            conf = arg

    if conf is None:
        print "Config file must be given. Usage: server.py -c <conf>'"
        sys.exit(2)

    c = ConfigParser.ConfigParser()
    c.readfp(open(conf))

    start_worker(c)
    start(c)    
