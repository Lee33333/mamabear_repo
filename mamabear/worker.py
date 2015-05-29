import logging
import requests
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

    def containers_for_app_image(self, db, app_name, image_tag):
        image_ref = self.image_ref(app_name, image_tag)
        return Container.get_by_ref(db, image_ref)
        
    def update_app_images(self, db, app):
        """
        Update images for app from docker registry. If we know
        about existing containers that reference a newly fetched
        image, we attach the containers to the image 
        """
        logging.info("Fetching images for {} from {} ...".format(app.name, self._registry_url))
        images = DockerWrapper.list_images(
            self._registry_url, app.name, self._registry_user, self._registry_password)
        for image_info in images:
            image = Image.get(db, image_info['layer'])
            if image:
                logging.info("Found existing image {}, updating tag to {}".format(image_info['layer'], image_info['name']))
                image.tag = image_info['name']
            else:
                logging.info("Found new image {}, setting tag to {}".format(image_info['layer'], image_info['name']))
                image = Image(id=image_info['layer'], tag=image_info['name'])

            for container in self.containers_for_app_image(db, app.name, image.tag):
                logging.info("Found container {} with state: [{}], associated with image: {}, linking".format(
                    container.id, container.state, image.id
                ))
                image.containers.append(container)
            
            app.images.append(image)
            db.add(image)
            db.add(app)
        db.commit()
                
    def update_deployment_containers(self, db, deployment):
        """
        Update container state for all containers on the deployment's configured hosts.
        """
        for host in deployment.hosts:
            logging.info("Updating containers for host: {}".format(host.hostname))
            self.update_host_containers(db, host)

        for container in self.containers_for_app_image(db, deployment.app_name, deployment.image_tag):
            logging.info("Found container {} with state: [{}], associated with deployment: {}, linking".format(
                container.id, container.state, deployment.name()
            ))
            deployment.containers.append(container)
        
        db.add(deployment)
        db.commit()

    def update_deployment_status(self, db, deployment):
        """
        Update app status for all of the deployment's containers
        """
        for container in deployment.containers:
            if container.state == 'running':
                status_url = "http://%s:%s/%s" % (
                    container.host.hostname,
                    deployment.status_port,
                    deployment.status_endpoint)
                r = requests.get(status_url)
                logging.info("Checking status of {} for container: {}".format(status_url, container.id))
                if r.ok:
                    container.status = 'up'
                    logging.info("App for Container: {} is [up]".format(container.id))
                else:
                    container.status = 'down'
                    logging.info("App for Container: {} is [down]".format(container.id))
            else:
                container.status = 'down'
        
    def update_host_containers(self, db, host):
        """
        For a given host, update the application status and container
        state for all containers.
        """
        wrapper = DockerWrapper(host.hostname, host.port, self._config)
        host_container_info = []
        try:
            host_container_info = wrapper.state_of_the_universe()
        except Exception as e:
            logging.error(e)
            host.status = 'down'
            db.add(host)
        
        for info in host_container_info:
            container = Container.get(db, info['id'])
            if container:
                logging.info("Found existing container {}, updating state to: {}".format(info['id'], info['state']))
                container.state = info['state']
                container.finished_at = parser.parse(info['finished_at']).astimezone(tz.tzlocal()).replace(tzinfo=None)
                db.add(container)
            else:
                logging.info("Got new container {}, setting state to: {}".format(info['id'], info['state']))
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
        """
        Updates every app and container state on all hosts
        """
        for host in db.query(Host).all():
            logging.info("Updating containers for host: {}".format(host.hostname))
            self.update_host_containers(db, host)
                    
    def update_all(self, db):        
        
        apps = db.query(App).all()
        for app in apps:
            logging.info("Updating image and deployment information for {}".format(app.name))
            try:
                self.update_app_images(db, app)
            except Exception as e:
                logging.error(e)
                db.rollback()
                
            for deployment in app.deployments:
                try:
                    self.update_deployment_containers(db, deployment)
                    self.update_deployment_status(db, deployment)
                except Exception as e:
                    logging.error(e)
                    db.rollback()
                    
        logging.info("Updating container information")
        try:
            self.update_all_containers(db)
        except Exception as e:
            logging.error(e)
            db.rollback()
