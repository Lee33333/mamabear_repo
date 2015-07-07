import boto
import cherrypy
#what is ConfigParser
import ConfigParser
from mock import patch
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from mamabear.model import *
from mamabear.worker import Worker
import mamabear.server
import mamabear.docker_wrapper
from mamabear.controllers import HostController, ImageController, DeploymentController, AppController

def get_session(engine):    
    sess = scoped_session(sessionmaker(autoflush=True,
                                       autocommit=False))
    sess.configure(bind=engine)
    return sess
            
def init_db(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def setup_module(module):
    module.engine = create_engine('sqlite://')
    init_db(module.engine)
            
def teardown_module(module):
    if module.engine:
        module.engine.dispose()
        module.engine = None

class BaseControllerTest(object):

    @staticmethod
    def data():
        return []
            
    def setup(self):
        self.controller = self._controller()
        self.db = get_session(engine)
        cherrypy.request.db = self.db
        self.db.add_all(self.data())

        hostname = '127.0.0.1'
        alias = 'Daria'
        port = 2376

        host = Host(hostname=hostname, alias=alias, status='up', port=port)             
        self.db.add(host)
        self.db.commit()

    def teardown(self):
        self.db.remove()

class TestHosts(BaseControllerTest):
    
    def _controller(self):
        return HostController()

    def test_get_host(self):

        host = self.controller.get_host('127.0.0.1')
        assert host['port'] == 2376
        assert host['hostname'] == u'127.0.0.1'
        assert host['status'] == u'up'
        assert host['alias'] == u'Daria'


