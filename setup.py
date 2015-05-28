# setup.py
from setuptools import setup, find_packages

version = '0.0.1'

setup(name='click2care-mamabear',
      version=version,
      description='Manages docker containers',
      install_requires=[
          'cherrypy', 'routes', 'sqlalchemy', 'mysql-python', 'docker-py', 'python-dateutil'],
      packages=find_packages(),
      py_modules=['mamabear',],
      include_package_data=True,
      zip_safe=False,
)
