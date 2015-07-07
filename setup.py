# setup.py
from setuptools import setup, find_packages

version = '0.0.1'

setup(name='click2care-mamabear',
      version=version,
      description='Manages docker containers',
      install_requires=[
          'cherrypy', 'apscheduler', 'routes', 'sqlalchemy', 'mysql-python',
          'docker-py', 'python-dateutil', 'pyopenssl', 'ndg-httpsclient',
          'pyasn1','nose', 'boto', 'mock',],
      packages=find_packages(),
      py_modules=['mamabear',],
      include_package_data=True,
      zip_safe=False,
)
