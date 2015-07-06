import unittest

#import boto
import cherrypy
#what is ConfigParser
import ConfigParser
from mock import patch
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
#import everything from model
from mamabear.model import *
from mamabear.worker import *
#import all the controllers from controllers.py
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

    def teardown(self):
        self.db.remove()

class TestHosts(BaseControllerTest):
    
    def _controller(self):
        return HostController()

    def test_add_host(self):
        cherrypy.request.json = {
            'host': {
                'hostname': '127.0.0.1',
                'alias': 'Daria',
                'port': 2376
            }
        }
        result = self.controller.add_host()
        host = self.controller.get_host('127.0.0.1')
        assert host['status'] == 'up'



