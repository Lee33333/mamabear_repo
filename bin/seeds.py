#!/usr/bin/env python

import sys
import json
import getopt
import ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from mamabear.model import *

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

def load_seeds(db):

    h1 = Host(hostname='10.10.10.20', port=2376)
    db.add(h1)

    d1 = Deployment(
        image_tag='10', environment='test', status_endpoint='/curator/v1/status',
        mapped_ports="9099:9099", hosts=[h1],
        env_vars=[EnvironmentVariable(property_key='ENV', property_value='test')])

    app1 = App(name='sagebear', deployments=[d1])
    db.add(app1)    
    
        
    

    
    
    
if __name__ == '__main__':
    argv = sys.argv[1:]
    conf = None
                              
    try:
        opts, args = getopt.getopt(argv, "hc:")
    except getopt.GetoptError:
        print 'Usage: seeds.py -c <config_file>'
        sys.exit(2)

    for opt, arg in opts:
        if opt == "-h":
            print 'Usage: seeds.py -c <config_file>'
        elif opt == "-c":
            conf = arg
                            
    if conf is None:
        print "Config file must be given. Usage: seeds.py -c <config_file>"
        sys.exit(2)

    c = ConfigParser.ConfigParser()
    c.readfp(open(conf))    

    db = get_session(get_engine(c))
    load_seeds(db)
    db.commit()
