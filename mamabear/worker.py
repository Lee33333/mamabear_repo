import logging
from dateutil import tz
from dateutil import parser
from datetime import datetime
from mamabear.model import *
from mamabear.docker_wrapper import DockerWrapper
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

logging.basicConfig(level=logging.INFO)

class Worker(object):
    """
    Class that makes use of the docker wrapper to
    update data in the db
    """

    def get_engine(self, config):
        return create_engine('mysql://%s:%s@%s/%s' % (
            config.get('mysql', 'user'),
            config.get('mysql', 'passwd'),
            config.get('mysql', 'host'),
            config.get('mysql', 'database')
        ), echo=False)    

    def get_session(self, engine):    
        sess = scoped_session(sessionmaker(autoflush=True,
                                       autocommit=False))
        sess.configure(bind=engine)
        return sess

    def __init__(self, config):
        db = self.get_session(self.get_engine(config))
        self._config = config
        # Just one registry is allowed for now, and is configured at
        # server launch time
        self._registry_url = config.get('registry', 'host')
        # Registry user is *required*
        self._registry_user = config.get('registry', 'user')
        self._registry_password = config.get('registry', 'password')            
        self.update_all(db)

    def image_ref(self, app_name, image_tag):
        return "%s/%s:%s" % (self._registry_user, app_name, image_tag)
        
    def update_images(self, db, app):        
        logging.info("Fetching images for {} from {} ...".format(app.name, self._registry_url))
        images = DockerWrapper.list_images(
            self._registry_url, app.name, self._registry_user, self._registry_password)
        for image_info in images:
            image = Image.get(db, image_info['layer'])
            if image:
                image.tag = image_info['name']
            else:
                image = Image(id=image_info['layer'], tag=image_info['name'])

            #
            # Link all containers associated with this image
            #
            image_ref = "%s/%s:%s" % (self._registry_user, app.name, image.tag)
            for container in Container.get_by_ref(db, image_ref):
                image.containers.append(container)
            
            app.images.append(image)
            db.add(image)
            db.add(app)
        db.commit()
                    

    def update_deployment_containers(self, db, deployment):
        for host in deployment.hosts:
            self.update_containers(db, host)
            
    def update_containers(self, db, host):
        wrapper = DockerWrapper(host.hostname, host.port, self._config)
        previous_containers = [c for c in host.containers]
        host_containers = set()

        # TODO: check health url too
        for info in wrapper.state_of_the_universe():
            container = Container.get(db, info['id'])
            if container:
                container.state = info['state']
                container.finished_at = parser.parse(info['finished_at']).astimezone(tz.tzlocal()).replace(tzinfo=None)
                db.add(container)
            else:
                # new container
                image_layer = info['image_id'][0:8]
                image = Image.get(db, image_layer)
                container = Container(
                    id=info['id'],
                    command=info['command'],
                    image_ref=info['image_ref'],
                    state = info['state'],
                    started_at = parser.parse(info['started_at']).astimezone(tz.tzlocal()).replace(tzinfo=None),
                    finished_at = parser.parse(info['finished_at']).astimezone(tz.tzlocal()).replace(tzinfo=None)
                )
                if image:
                    container.image = image
                host.containers.append(container)
                db.add(container)
                db.add(host)

        db.commit()
                        
    def update_all_containers(self, db):
        # Get all running containers
        for host in db.query(Host).all():            
            self.update_containers(db, host)

    def update_deployment_containers(self, db, deployment):
        image_ref = self.image_ref(deployment.app_name, deployment.image_tag)
                
        for deployment_host in deployment.hosts:
            host_app_containers = [c for c in deployment_host.containers if c.image_ref == image_ref]
            deployment.containers.extend(host_app_containers)
                    
        db.add(deployment)
        db.commit()
                
    def update_all(self, db):        
        
        apps = db.query(App).all()
        for app in apps:
            logging.info("Updating image and deployment information for {}".format(app.name))
            
            # Get images from configured registry first
            try:
                self.update_images(db, app)
            except Exception as e:
                logging.error(e)
                db.rollback()
                
            for deployment in app.deployments:
                try:
                    self.update_deployment_containers(db, deployment)
                except Exception as e:
                    logging.error(e)
                    db.rollback()
                    
        logging.info("Updating container information")
        try:
            self.update_all_containers(db)
        except Exception as e:
            logging.error(e)
            db.rollback()
