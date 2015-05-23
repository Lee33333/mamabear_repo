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


    c1 = Container(
        id='c6d721ae26deb39871c6c4837f4c0f2992f7251a75fd10f24365dfsagebear0',
        command='/var/lib/sagebear/server.py', status='ok')
    c2 = Container(
        id='c6d721ae26deb39871c6c4837f4c0f2992f7251a75fd10f24365dfcarebear0',
        command='/var/lib/carebear/server.py', status='ok')
    c3 = Container(
        id='c6d721ae26deb39871c6c4837f4c0f2992f7251a75fd10f24365df88curator0',
        command='/var/lib/curator/server.py', status='ok')
    c4 = Container(
        id='c6d721ae26deb39871c6c4837f4c0f2992f7251a75fd10f24365dfsagebear1',
        command='/var/lib/sagebear/server.py', status='ok')

    
    h1 = Host(hostname='10.0.0.1', port=2347, type='deployment', containers=[c1, c2, c3])
    h2 = Host(hostname='10.0.0.2', port=2347, type='deployment', containers=[c1, c2, c3])
    h3 = Host(hostname='10.0.0.3', port=2347, type='deployment', containers=[c4])
    r = Host(hostname='http://registry.hub.docker.com', type='registry')
    
    image1 = Image(
        id='c6d721ae26deb39871c6c4837f4c0f2992f7251a75fd10f24365df88sagebear',
        tag='1', containers=[c1, c4])
    image2 = Image(
        id='b6d721ae26deb39871c6c4837f4c0f2992f7251a75fd10f24365df88carebear',
        tag='2', containers=[c2])
    image3 = Image(
        id='e6d721ae26deb39871c6c4837f4c0f2992f7251a75fd10f24365df881curator',
        tag='1', containers=[c3])

    d1 = Deployment(
        environment='test', status_endpoint='/curator/v1/status',
        mapped_ports="9099:9099", hosts=[h1, h2], containers=[c3])
    d2 = Deployment(
        environment='test', status_endpoint='/carebear/v1/status',
        mapped_ports="9001:9001", hosts=[h1, h2], containers=[c2])
    d3 = Deployment(
        environment='prod', status_endpoint='/sagebear/v1/status',
        mapped_ports="9041:9041",
        mapped_volumes="/var/log/docker:/var/log/docker",
        hosts=[h1, h2, h3], containers=[c1,c4])

    app1 = App(name='sagebear', images=[image1], deployments=[d3])
    app2 = App(name='carebear', images=[image2], deployments=[d2])
    app3 = App(name='curator', images=[image3], deployments=[d1])

    containers = [c1, c2, c3, c4]
    hosts = [h1, h2, h3, r]
    images = [image1, image2, image3]
    deployments = [d1, d2, d3]
    apps = [app1, app2, app3]
    db.add_all(containers)
    db.add_all(hosts)
    db.add_all(images)
    db.add_all(deployments)
    db.add_all(apps)
    
    
        
    

    
    
    
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
