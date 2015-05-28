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
    hostname = Column(String(200), index=True, unique=True)
    port = Column(Integer)
    asg_name = Column(String(200), ForeignKey("aws_asgs.group_name"), index=True)
    containers = relationship("Container", backref="host")

    @staticmethod
    def create(session, data):
        hostname = data.get('hostname')
        port = data.get('port')
        asg_name = data.get('asg_name')

        if hostname:
            host = Host(hostname=hostname)
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
            'port': self.port,
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
    def get(session, image_id):
        return session.query(Image).get(image_id)

    @staticmethod
    def find_by_name_and_tag(session, app_name, image_tag):
        q = Image.list_query(app_name=app_name, image_tag=image_tag)
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
    status = Column(String(100), index=True)

    # This is container status itself
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    # One of 'running', 'stopped', 'paused', 'restarting', or 'dead'
    state = Column(String(100), index=True)
                   
    image_ref = Column(String(200), index=True)
    
    deployment_id = Column(Integer, ForeignKey("deployments.id"))    
    image_id = Column(CHAR(8), ForeignKey("images.id"))
    host_id = Column(Integer, ForeignKey("hosts.id"))        

    @staticmethod
    def get_by_ref(session, image_ref):
        return session.query(Container).filter(Container.image_ref == image_ref)
        
    @staticmethod
    def get(session, container_id):
        return session.query(Container).get(container_id)
        
    def encode(self):
        result = {
            'host': self.host.hostname,
            'status': self.status,
            'command': self.command
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
            'image_count': len(self.images),
            'container_count': sum([len(d.containers) for d in self.deployments])
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
    status_endpoint = Column(String(200), nullable=False)
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
    
    required_keys = ['image_tag', 'app_name', 'environment', 'status_endpoint']

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

    @staticmethod
    def create(session, data):
        if all(k in data for k in Deployment.required_keys):
            d = Deployment(
                image_tag=data['image_tag'],
                app_name=data['app_name'],
                environment=data['environment'],
                status_endpoint=data['status_endpoint']
            )
            if 'status_port' in data:
                d.status_port = data['status_port']
                
            if 'links' in data:
                for link in data['links']:
                    image = Image.find_by_name_and_tag(
                        session, link['app_name'], link['image_tag'])
                    if image:
                        d.links.append(image)
                        
            if 'volumes' in data:
                for vol in data['volumes']:
                    image = Image.find_by_name_and_tag(
                        session, link['app_name'], link['image_tag'])
                    if image:
                        d.volumes.append(image)
                        
            if 'mapped_ports' in data and len(data['mapped_ports']) > 0:
                # FIXME: do some validation of structure here
                d.mapped_ports = ','.join(data['mapped_ports'])
            if 'mapped_volumes' in data and len(data['mapped_volumes']) > 0:
                # FIXME: do some validation of structure here
                d.mapped_volumes = ','.join(data['mapped_volumes'])
            if 'parent' in data:
                d.parent_id = data['parent']
            if 'environment_variables' in data:
                for var in data['environment_variables']:
                    value = data['environment_variables'][var]
                    d.env_vars.append(EnvironmentVariable(property_key=var, property_value=value))
            if 'hosts' in data:
                for name in data['hosts']:
                    host = Host.get_by_name(session, name)
                    if host:
                        d.hosts.append(host)
                    # FIXME: What should we do when the host specified isn't configured?
            try:
                session.add(d)
                session.commit()
                return d
            except:
                session.rollback()
                traceback.print_exc()

                
    def encode(self):
        ports = self.mapped_ports.split(',') if self.mapped_ports else []
        volumes = self.mapped_volumes.split(',') if self.mapped_volumes else []
        return {
            'environment': self.environment,
            'parent': self.parent_id,
            'image_tag': self.image_tag,
            'app_name': self.app_name,
            'status_endpoint': self.status_endpoint,
            'status_port': self.status_port,
            'mapped_ports': ports,
            'mapped_volumes': volumes,
            'hosts': [host.hostname for host in self.hosts],
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
