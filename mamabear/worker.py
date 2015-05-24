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
        self._db = self.get_session(self.get_engine(config))
        # Just one registry is allowed for now, and is configured at
        # server launch time
        self._registry_url = config.get('registry', 'host')
        # Registry user is *required*
        self._registry_user = config.get('registry', 'user')
        self._registry_password = config.get('registry', 'password')
        
        self._deployment_hosts = Host.list(self._db)
        self._docker_clients = [
            DockerWrapper(h['hostname'], h['port'], config) for h in self._deployment_hosts]
        self.update_all()

    def update_images(self, app):        
        logging.info("Fetching images for {} from {} ...".format(app.name, self._registry_url))
        images = DockerWrapper.list_images(
            self._registry_url, app.name, self._registry_user, self._registry_password)
        for image_info in images:
            image = Image.get(self._db, image_info['layer'])
            if image:
                image.tag = image_info['name']
            else:
                image = Image(id=image_info['layer'], tag=image_info['name'])

            #
            # Link all containers associated with this image
            #
            image_ref = "%s/%s:%s" % (self._registry_user, app.name, image.tag)
            for container in Container.get_by_ref(self._db, image_ref):
                image.containers.append(container)
            
            app.images.append(image)
            self._db.add(image)
            self._db.add(app)
        self._db.commit()
                    

    def update_containers(self):
        # Get all running containers
        for dc in self._docker_clients:            
            host = Host.get_by_name(self._db, dc.host)
            if host:
                previous_containers = [c for c in host.containers]
                host_containers = set()
                
                for container_info in dc.ps():                
                    container = Container.get(self._db, container_info['Id'])
                    if container:
                        # update status
                        container.status = container_info['Status']
                        self._db.add(container)
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
                        self._db.add(container)
                        self._db.add(host)
                    
                # Manage containers dropping off the list
                for previous_container in previous_containers:
                    if not previous_container.id in host_containers:
                        logging.info(
                            "Previously running container {} not found, setting status to DONE".format(previous_container.id))
                        previous_container.status = "DONE"
                        self._db.add(previous_container)
                    
        self._db.commit()
                
    def update_all(self):        

        logging.info("Updating container information")
        self.update_containers()
        
        apps = self._db.query(App).all()
        for app in apps:
            logging.info("Updating image and deployment information for {}".format(app.name))
            
            # Get images from configured registry first
            self.update_images(app)
            for deployment in app.deployments:
                image_ref = "%s/%s:%s" % (self._registry_user, app.name, deployment.image_tag)
                
                for deployment_host in deployment.hosts:
                    host_app_containers = [c for c in deployment_host.containers if c.image_ref == image_ref]
                    deployment.containers.extend(host_app_containers)
                    
                self._db.add(deployment)
                
            self._db.commit()
                    
