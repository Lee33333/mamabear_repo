
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import relationship, backref, load_only
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey, ForeignKeyConstraint, Table
from sqlalchemy import asc, desc, or_, and_, not_, CHAR, TIMESTAMP, Text, DateTime, Column, BigInteger, Integer, String

Base = declarative_base()

class Host(Base):
    __tablename__ = "hosts"

    id = Column(Integer, autoincrement=True, primary_key=True)
    hostname = Column(String(200), index=True)
    port = Column(Integer)
    
    containers = relationship("Container", backref="host")

    @staticmethod
    def get_by_name(session, hostname):
        h = session.query(Host).filter(Host.hostname == hostname).limit(1).one()
        return h

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
        return {
            'hostname': self.hostname,
            'port': self.port
        }
        
class Image(Base):
    __tablename__ = "images"

    id = Column(CHAR(8), primary_key=True)
    tag = Column(String(200), index=True)
    app_name = Column(String(200), ForeignKey("apps.name"), index=True)
    containers = relationship("Container", backref="image")
            
    @staticmethod
    def get(session, image_id):
        return session.query(Image).get(image_id)
        
    def encode(self):
        return {
            'id': self.id,
            'tag': self.tag
        }
        
class Container(Base):
    __tablename__ = "containers"

    id = Column(CHAR(64), primary_key=True)
    command = Column(String(200))
    status = Column(String(100), index=True)
    
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
        return {
            'image': self.image.encode(),
            'host': self.host.hostname,
            'status': self.status,
            'command': self.command
        }
        
class App(Base):
    __tablename__ = "apps"

    name = Column(String(200), primary_key=True)

    deployments = relationship("Deployment", backref="app")
    images = relationship("Image", backref="app")

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
        return [a.name for a in q.all()]
        
deployment_hosts = Table(
    'deployment_hosts', Base.metadata,
    Column('host_id', Integer, ForeignKey("hosts.id")),
    Column('deployment_id', Integer, ForeignKey("deployments.id")))

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, autoincrement=True, primary_key=True)    
    image_tag = Column(String(200))
    app_name = Column(String(200), ForeignKey("apps.name"))
    environment = Column(String(4), index=True)
    status_endpoint = Column(String(200))
    mapped_ports = Column(Text)
    mapped_volumes = Column(Text)

    parent_id = Column(Integer, ForeignKey("deployments.id"))
    parent = relationship("Deployment", remote_side=[id], backref="child")
    
    env_vars = relationship("EnvironmentVariable", foreign_keys="EnvironmentVariable.id", cascade="all, delete-orphan")
    hosts = relationship("Host", secondary=deployment_hosts, backref="deployments")
    containers = relationship("Container", backref="deployment")

    def encode(self):
        ports = self.mapped_ports.split(',') if self.mapped_ports else []
        volumes = self.mapped_volumes.split(',') if self.mapped_volumes else []
        return {
            'environment': self.environment,
            'status_endpoint': self.status_endpoint,
            'mapped_ports': ports,
            'mapped_volumes': volumes,
            'hosts': [host.hostname for host in self.hosts],
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
