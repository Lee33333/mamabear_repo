import logging
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
                
        for container_info in wrapper.ps():                
            container = Container.get(db, container_info['Id'])
            if container:
                # update status
                container.status = container_info['Status']
                db.add(container)
                host_containers.add(container.id)
            else:
                # create new container
                container = Container(
                    id=container_info['Id'],
                    command=container_info['Command'],
                    status=container_info['Status'],
                    image_ref=container_info['Image']
                )
                host_containers.add(container.id)
                host.containers.append(container)
                db.add(container)
                db.add(host)
                    
        # Manage containers dropping off the list
        for previous_container in previous_containers:
            if not previous_container.id in host_containers:
                logging.info(
                    "Previously running container {} not found, setting status to DONE".format(previous_container.id))
                previous_container.status = "DONE"
                db.add(previous_container)
                
        db.commit()
                        
    def update_all_containers(self, db):
        # Get all running containers
        for host in db.query(Host).all():            
            self.update_containers(db, host)
                
    def update_all(self, db):        

        logging.info("Updating container information")
        try:
            self.update_all_containers(db)
        except Exception as e:
            logging.error(e)
            db.rollback()
        
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
                image_ref = "%s/%s:%s" % (self._registry_user, app.name, deployment.image_tag)
                
                for deployment_host in deployment.hosts:
                    host_app_containers = [c for c in deployment_host.containers if c.image_ref == image_ref]
                    deployment.containers.extend(host_app_containers)
                    
                db.add(deployment)
                
            db.commit()
                    
