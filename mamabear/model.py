import traceback
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import relationship, backref, load_only
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey, ForeignKeyConstraint, Table
from sqlalchemy import asc, desc, or_, and_, not_, CHAR, TIMESTAMP, Text, DateTime, Column, BigInteger, Integer, String

Base = declarative_base()

class Host(Base):
    __tablename__ = "hosts"
    id = Column(Integer, autoincrement=True, primary_key=True)
    alias = Column(String(200), index=True, unique=True, nullable=False)
    hostname = Column(String(200), index=True, unique=True)
    port = Column(Integer)
    status = Column(String(4), index=True)
    asg_name = Column(String(200), ForeignKey("aws_asgs.group_name"), index=True)
    containers = relationship("Container", backref="host")

    VALID_STATUS = ['up', 'down']

    @staticmethod
    def delete_by_alias(session, alias):
        q = session.query(Host).filter(Host.alias == alias).limit(1)
        if q.count() == 1:
            h = q.one() 
            for container in h.containers:
                session.delete(container)
            session.delete(h)
            return True
        return False

    @staticmethod
    def create(session, data):
        hostname = data.get('hostname')
        alias = data.get('alias')
        port = data.get('port')
        asg_name = data.get('asg_name')

        if hostname:
            host = Host(hostname=hostname, alias=alias, status='up')
            if port:
                host.port = port                
            if asg_name:
                host.asg_name = asg_name
            try:
                session.add(host)
                session.commit()
            except Exception as e:
                session.rollback()
                traceback.print_exc()
                return
            return host
                
    @staticmethod
    def get_by_name(session, hostname):
        h = session.query(Host).filter(Host.hostname == hostname).limit(1)
        if h.count() == 1:
            return h.one()

    @staticmethod    
    def list_query(session):
        q = session.query(Host)
        return q

    @staticmethod
    def count(session):
        q = Host.list_query(session)
        return q.count()

    @staticmethod
    def list(session):
        q = Host.list_query(session)
        return [h.encode() for h in q.all()]
    
    def encode(self):
        encoded = {
            'hostname': self.hostname,
            'alias': self.alias,
            'port': self.port,
            'status': self.status,
            'container_count': len(self.containers),
            'containers': [c.encode() for c in self.containers]
        }
        if self.asg_name:
            encoded['asg_name'] = self.asg_name
        return encoded
        
class Image(Base):
    __tablename__ = "images"

    id = Column(CHAR(8), primary_key=True)
    tag = Column(String(200), index=True)
    app_name = Column(String(200), ForeignKey("apps.name"), index=True)
    containers = relationship("Container", backref="image")

    @staticmethod
    def delete(session, image_id):
        image = Image.get(session, image_id)
        if image:
            for container in image.containers:
                session.delete(container)
            session.delete(image)
            return True
        return False
        
    @staticmethod
    def get(session, image_id):
        return session.query(Image).get(image_id)

    @staticmethod
    def find_by_name_and_tag(session, app_name, image_tag):
        q = Image.list_query(session, app_name=app_name, image_tag=image_tag)
        if q.count() > 0:
            return q.limit(1).one()
            
    @staticmethod    
    def list_query(session, app_name=None, image_tag=None):
        q = session.query(Image)
        if app_name:
            q = q.filter(Image.app_name.like('%'+app_name+'%'))
        if image_tag:
            q = q.filter(Image.tag.like('%'+image_tag+'%'))
        return q

    @staticmethod
    def count(session, app_name=None, image_tag=None):
        q = Image.list_query(session, app_name=app_name, image_tag=image_tag)
        return q.count()

    @staticmethod
    def list(session, app_name=None, image_tag=None, order='asc',
             sort_field='app_name', limit=10, offset=0):
        q = Image.list_query(session, app_name=app_name, image_tag=image_tag)

        if order == 'asc':
            q = q.order_by(asc(getattr(Image, sort_field)))
        else:
            q = q.order_by(desc(getattr(Image, sort_field)))
            
        q = q.limit(limit).offset(offset)

        return [r.encode() for r in q.all()]

    def encode(self):
        return {
            'app_name': self.app_name,
            'id': self.id,
            'tag': self.tag
        }
        
class Container(Base):
    __tablename__ = "containers"

    id = Column(CHAR(64), primary_key=True)
    command = Column(String(200))
    
    # This will be the endpoint status, via deployment
    status = Column(String(4), index=True)

    # This is container status itself
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    state = Column(String(12), index=True)
                   
    image_ref = Column(String(200), index=True)
    
    deployment_id = Column(Integer, ForeignKey("deployments.id"))    
    image_id = Column(CHAR(8), ForeignKey("images.id"))
    host_id = Column(Integer, ForeignKey("hosts.id"))        

    VALID_STATUS = ['up', 'down']
    VALID_STATES = ['running', 'stopped', 'paused', 'restarting', 'dead']

    
    @staticmethod    
    def list_query(session, app_name=None, image_tag=None, host_name=None,
                   status=None, container_state=None, command=None):
        q = session.query(Container)
        if app_name:            
            q = q.join(Container.image).filter(Image.app_name.like('%'+app_name+'%'))
        if image_tag:
            q = q.join(Container.image).filter(Image.tag.like('%'+image_tag+'%'))
        if host_name:
            q = q.join(Container.host).filter(Host.hostname.like('%'+host_name+'%'))
        if status:
            q = q.filter(Container.status == status)
        if container_state:
            q = q.filter(Container.state == container_state)
        if command:
            q = q.filter(Container.command.like('%'+command+'%'))
        return q

    @staticmethod
    def count(session, app_name=None, image_tag=None, host_name=None,
              status=None, container_state=None, command=None):
        q = Container.list_query(session, app_name=app_name, image_tag=image_tag,
                                 host_name=host_name, status=status,
                                 container_state=container_state, command=command)
        return q.count()

    @staticmethod
    def list(session, app_name=None, image_tag=None, host_name=None,
             status=None, container_state=None, command=None, order='asc',
             sort_field='started_at', limit=10, offset=0):
        q = Container.list_query(session, app_name=app_name, image_tag=image_tag,
                                 host_name=host_name, status=status,
                                 container_state=container_state, command=command)
        if order == 'asc':
            q = q.order_by(asc(getattr(Container, sort_field)))
        else:
            q = q.order_by(desc(getattr(Container, sort_field)))
            
        q = q.limit(limit).offset(offset)

        return [r.encode() for r in q.all()]
        
    @staticmethod
    def get_by_ref(session, image_ref):
        return session.query(Container).filter(Container.image_ref == image_ref).all()
        
    @staticmethod
    def get(session, container_id):
        return session.query(Container).get(container_id)
        
    def encode(self):
        result = {
            'id': self.id,
            'host': self.host.hostname,
            'status': self.status,
            'command': self.command,
            'started_at': self.started_at.strftime('%Y-%m-%d %H:%M:%S'),
            'finished_at': self.finished_at.strftime('%Y-%m-%d %H:%M:%S'),
            'state': self.state
        }
        if self.image:
            result['image'] = self.image.encode()
        return result
        
class App(Base):
    __tablename__ = "apps"

    name = Column(String(200), primary_key=True)

    deployments = relationship("Deployment", backref="app")
    images = relationship("Image", backref="app")

    @staticmethod
    def delete(session, name):
        app = App.get(session, name)
        if app:
            for d in app.deployments:
                Deployment.delete(session, d.app_name, d.image_tag, d.environment)
            for i in app.images:
                Image.delete(session, i.id)
            session.delete(app)
            return True
        return False
        
    @staticmethod
    def create(session, name):
        if name:
            app = App(name=name)
            try:
                session.add(app)
                session.commit()
            except Exception as e:
                session.rollback()
                traceback.print_exc()
                return
            return app
            
    @staticmethod
    def get(session, name):
        return session.query(App).get(name)
        
    @staticmethod    
    def list_query(session, name=None):
        q = session.query(App)
        if name:
            q = q.filter(App.name.like('%'+name+'%'))
        return q

    @staticmethod
    def count(session, name=None):
        q = App.list_query(session, name)
        return q.count()

    @staticmethod
    def list(session, name=None):
        q = App.list_query(session, name)
        return [a.encode() for a in q.all()]

    def encode(self):
        return {
            'name': self.name,
            'images': [image.encode() for image in self.images],
            'deployments': [d.encode() for d in self.deployments]
        }
        
deployment_hosts = Table(
    'deployment_hosts', Base.metadata,
    Column('host_id', Integer, ForeignKey("hosts.id")),
    Column('deployment_id', Integer, ForeignKey("deployments.id")))

deployment_links = Table(
    'deployment_links', Base.metadata,
    Column('image_id', CHAR(8), ForeignKey("images.id")),
    Column('deployment_id', Integer, ForeignKey("deployments.id")))

deployment_volumes = Table(
    'deployment_volumes', Base.metadata,
    Column('image_id', CHAR(8), ForeignKey("images.id")),
    Column('deployment_id', Integer, ForeignKey("deployments.id")))

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, autoincrement=True, primary_key=True)    
    image_tag = Column(String(200), nullable=False, index=True)
    app_name = Column(String(200), ForeignKey("apps.name"), index=True, nullable=False)
    environment = Column(String(4), index=True, nullable=False)
    status_endpoint = Column(String(200), nullable=False, default='/')
    status_port = Column(Integer)
    mapped_ports = Column(Text)
    mapped_volumes = Column(Text)

    parent_id = Column(Integer, ForeignKey("deployments.id"))
    parent = relationship("Deployment", remote_side=[id], backref="child")
    
    env_vars = relationship("EnvironmentVariable", foreign_keys="EnvironmentVariable.id", cascade="all, delete-orphan")
    hosts = relationship("Host", secondary=deployment_hosts, backref="deployments")
    containers = relationship("Container", backref="deployment")
    
    links = relationship("Image", secondary=deployment_links)
    volumes = relationship("Image", secondary=deployment_volumes)
    
    required_keys = ['image_tag', 'app_name', 'environment']

    def name(self):
        return "%s:%s, %s" % (self.app_name, self.image_tag, self.environment)

    @staticmethod
    def update_by_app(session, app_name, image_tag, environment, data):
        deployment = Deployment.get_by_app(session, app_name,
                                           image_tag=image_tag,
                                           environment=environment)
        if deployment:
            Deployment.update_with_data(session, deployment, data)
            return True
        return False
        
    @staticmethod
    def update_with_data(session, deployment, data):
        if 'status_endpoint' in data:
            deployment.status_endpoint = data['status_endpoint']
        if not deployment.status_endpoint:
            deployment.status_endpoint = '/'
            
        if 'status_port' in data:
            deployment.status_port = data['status_port']

        #
        # FIXME = the linked hosts and volumes (below) should
        # be deployments not images
        #
        if 'links' in data:
            #delete links
            deployment.links = []
            for link in data['links']:
                image = Image.find_by_name_and_tag(
                    session, link['app_name'], link['image_tag'])
                if image:
                    deployment.links.append(image)

                        
        if 'volumes' in data:
            #delete volumes
            deployment.volumes = []
            for vol in data['volumes']:
                image = Image.find_by_name_and_tag(
                    session, vol['app_name'], vol['image_tag'])
                if image:
                    deployment.volumes.append(image)

        if 'environment_variables' in data:
            deployment.env_vars = []
            for var in data['environment_variables']:
                value = data['environment_variables'][var]
                deployment.env_vars.append(EnvironmentVariable(property_key=var, property_value=value))

        if 'mapped_ports' in data and len(data['mapped_ports']) > 0:
            # FIXME: do some validation of structure here
            deployment.mapped_ports = ','.join(data['mapped_ports'])
        if 'mapped_ports' in data and data['mapped_ports'] == []:
            deployment.mapped_ports = None

        if 'mapped_volumes' in data and len(data['mapped_volumes']) > 0:
            # FIXME: do some validation of structure here
            deployment.mapped_volumes = ','.join(data['mapped_volumes'])
        if 'mapped_volumes' in data and data['mapped_volumes'] == []:
            deployment.mapped_volumes = None

        if 'parent' in data:
            deployment.parent_id = data['parent']

        if 'hosts' in data:
            deployment.hosts = [] # Overwrite hosts with these new hosts
            for name in data['hosts']:
                host = Host.get_by_name(session, name)
                if host:
                    deployment.hosts.append(host)
                    # FIXME: What should we do when the host specified isn't configured?            
    
    @staticmethod
    def create(session, data):
        if all(k in data for k in Deployment.required_keys):
            d = Deployment(
                image_tag=data['image_tag'],
                app_name=data['app_name'],
                environment=data['environment']
            )
            Deployment.update_with_data(session, d, data)
            try:
                session.add(d)
                session.commit()
                return d
            except:
                session.rollback()
                traceback.print_exc()
                
    @staticmethod
    def delete(session, app_name, image_tag, environment):
        deployment = Deployment.get_by_app(session, app_name, image_tag, environment)
        if deployment:
            for ev in deployment.env_vars:
                session.delete(ev)                
            session.delete(deployment)
            return True
        return False
        
    @staticmethod    
    def list_query(session, app_name=None, image_tag=None, environment=None):
        q = session.query(Deployment)
        if app_name:
            q = q.filter(Deployment.app_name.like('%'+app_name+'%'))
        if image_tag:
            q = q.filter(Deployment.image_tag.like('%'+image_tag+'%'))
        if environment:
            q = q.filter(Deployment.environment.like('%'+environment+'%'))            
        return q

    @staticmethod
    def count(session, app_name=None, image_tag=None, environment=None):
        q = Deployment.list_query(session, app_name=app_name, image_tag=image_tag, environment=environment)
        return q.count()

    @staticmethod
    def list(session, app_name=None, image_tag=None, environment=None,
             order='asc', sort_field='app_name', limit=10, offset=0):
        q = Deployment.list_query(session, app_name=app_name, image_tag=image_tag, environment=environment)

        if order == 'asc':
            q = q.order_by(asc(getattr(Deployment, sort_field)))
        else:
            q = q.order_by(desc(getattr(Deployment, sort_field)))
            
        q = q.limit(limit).offset(offset)

        return [r.encode() for r in q.all()]
        
    @staticmethod
    def get_by_app(session, app_name, image_tag=None, environment=None):
        q = session.query(Deployment).filter(Deployment.app_name == app_name)
        if image_tag:
            q = q.filter(Deployment.image_tag == image_tag)
        if environment:
            q = q.filter(Deployment.environment == environment)
        q = q.limit(1)
        if q.count() == 1:
            return q.one()

    def encode_with_deps(self, session):
        result = {'deployment': self.encode(), 'dependencies':[]}
        children = dict([(image.id, image) for image in self.links+self.volumes])
        for child_id in children:
            child = children[child_id]
            child_deployment = Deployment.get_by_app(
                session, child.app_name, child.tag, self.environment)
            if child_deployment:
                result['dependencies'].append(child_deployment.encode_with_deps(session))
        return result
            
    def encode(self):
        ports = self.mapped_ports.split(',') if self.mapped_ports else []
        volumes = self.mapped_volumes.split(',') if self.mapped_volumes else []
        return {
            'id': self.id,
            'environment': self.environment,
            'parent': self.parent_id,
            'image_tag': self.image_tag,
            'app_name': self.app_name,
            'status_endpoint': self.status_endpoint,
            'status_port': self.status_port,
            'mapped_ports': ports,
            'mapped_volumes': volumes,
            'hosts': [{'hostname': host.hostname, 'alias': host.alias} for host in self.hosts],
            'links': [image.encode() for image in self.links],
            'volumes': [image.encode() for image in self.volumes],
            'containers': [c.encode() for c in self.containers],
            'environment_variables': dict([(p.property_key, p.property_value) for p in self.env_vars])
        }

class EnvironmentVariable(Base):
    __tablename__ = "environment_variables"

    id = Column(Integer, ForeignKey("deployments.id"), primary_key=True)
    property_key = Column(String(100), primary_key=True, index=True)
    property_value = Column(Text, nullable=False)

    def _encode(self):
        return {
            'property_key': self.property_key,
            'property_value': self.property_value
        }

class AWSAutoScalingGroup(Base):
    """
    Auto-update available hosts using amazon's autoscaling
    group feature
    """
    __tablename__ = "aws_asgs"

    group_name = Column(String(200), primary_key=True)

    hosts = relationship("Host", backref="auto_scaling_group")

    @staticmethod
    def get(session, group_name):
        return session.query(AWSAutoScalingGroup).get(group_name)
