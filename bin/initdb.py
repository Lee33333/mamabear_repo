#!/usr/bin/env python
import sys
import getopt
import logging
import ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from mamabear.model import *

logging.basicConfig(level=logging.INFO)

def get_engine(config):
    return create_engine('mysql://%s:%s@%s/%s' % (
        config.get('mysql', 'user'),
        config.get('mysql', 'passwd'),
        config.get('mysql', 'host'),
        config.get('mysql', 'database')
    ), echo=False)    

def get_session(engine):    
    sess = scoped_session(sessionmaker(autoflush=True,
                                       autocommit=False))
    sess.configure(bind=engine)
    return sess
            
def init_db(config, engine=None):
    if not engine:
        engine = get_engine(config)
        
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
def init_db_once(config):
    engine = get_engine(config)
    if not App.__table__.exists(engine):
        init_db(config, engine=engine)

def update_metadata(config):
    engine = get_engine(config)
    Base.metadata.create_all(engine)


if __name__ == '__main__':
    argv = sys.argv[1:]
    conf = None
    force = None
    metadata_only = None
    
    try:
        opts, args = getopt.getopt(argv, "hc:f:m:")
    except getopt.GetoptError:
        print 'Usage: initdb.py -c <configFile>'
        sys.exit(2)

    for opt, arg in opts:
        if opt == "-h":
            print 'Usage: initdb.py -c <configFile>'
        elif opt == "-c":
            conf = arg
        elif opt == "-f":
            force = arg
        elif opt == "-m":
            metadata_only = arg 

    if conf is None:
        print "Config file must be given. Usage: initdb.py -c <conf>'"
        sys.exit(2)

    c = ConfigParser.ConfigParser()
    c.readfp(open(conf))

    if force and force == 'true':
        logging.info("Forcing database refresh...all data will need to be reloaded")
        init_db(c)
    elif metadata_only and metadata_only == 'true':
        logging.info("Updating database schema metadata")
        update_metadata(c)
    else:
        logging.info("Initializing new database")
        init_db_once(c)
