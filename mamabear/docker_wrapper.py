import time
import docker
import requests
import logging

logging.basicConfig(level=logging.INFO)

class DockerWrapper(object):

    def __init__(self, docker_host, docker_port, config, retry=3):
        self.host = docker_host
        self.port = docker_port
        self.retry = retry # how many times to retry docker client requests
        self.registry_user = config.get('registry', 'user')
        
        self._tls_conf = docker.tls.TLSConfig(
            assert_hostname=False,
            verify=False,
            client_cert=(
                config.get('docker', 'client_cert'),
                config.get('docker', 'client_key')
            ))
        self._client = docker.Client(
            base_url='https://%s:%s' % (docker_host, docker_port),
            timeout=10, # 10 second timeout
            tls=self._tls_conf
        )

    @staticmethod
    def list_images(registry_url, app_name, username, password=None):
        url = "%s/repositories/%s/%s/tags" % (registry_url, username, app_name)
        logging.info("Fetching url: {}".format(url))
        if password:
            r = requests.get(url, auth=(username, password))
        else:
            r = requests.get(url)
        if r.ok:
            return r.json()
        r.raise_for_status()

    def _state_from_detail(self, s):
        if (s['Dead']):
            return 'dead'
        elif (s['Paused']):
            return 'paused'
        elif (s['Restarting']):
            return 'restarting'
        elif (s['Running']):
            return 'running'
        else:
            return 'stopped'
            
    def state_of_the_universe(self):
        """
        High level function to list all containers,
        and cherry picked detail information 
        """
        universe = []
        for info in self.ps(all=True):
            cid = info['Id']
            detail = self.inspect(cid)
            data = {
                'id': cid,
                'image_id': detail['Image'],
                'image_ref': info['Image'],        
                'state': self._state_from_detail(detail['State']),
                'started_at': detail['State']['StartedAt'],
                'finished_at': detail['State']['FinishedAt']
            }
            if detail['Config']['Cmd']:
                data['command'] = ' '.join(detail['Config']['Cmd'])
            universe.append(data)
        return universe

    def _client_request(self, method, *args, **kwargs):
        """
        Deal with the fact that the docker-py client has no
        retry logic.
        """
        last_exception = None
        _method = getattr(self._client, method)
        for i in range(1, self.retry+1):
            try:
                return _method(*args, **kwargs)
            except Exception as e:
                logging.warn("Failed to run client method: {}, reason: [{}]".format(method, e.message))
                time.sleep(5)
                last_exception = e
        else:
            raise last_exception
            
    def ps(self, **kwargs):
        return self._client_request('containers', **kwargs)        

    def inspect(self, container_id):
        return self._client_request('inspect_container', container_id)
        
    def logs(self, container_id, stderr=False, stdout=False, stream=False, tail=10):
        return self._client_request('logs', container_id, stderr=stderr,
                                    stdout=stdout, stream=stream, tail=tail)

    def pull(self, app_name):
        return self._client_request('pull', app_name)

    def rm(self, container_id):
        return self._client_request('remove_container', container_id)

    def stop(self, container_id):
        return self._client_request('stop', container_id)

    def create_container(self, **kwargs):
        return self._client_request('create_container', **kwargs)

    def start_container(self, container):
        return self._client_request('start', container=container.get('Id'))

    def deploy_with_deps(self, tree):
        deployment = tree['deployment']
        dependencies = tree['dependencies']
        for dependency in dependencies:
            self.deploy_with_deps(dependency)

        logging.info("Deploying {}:{}".format(
            deployment.get('app_name'), deployment.get('image_tag')))
        self.deploy(deployment)
        
    def run_with_deps(self, tree):
        deployment = tree['deployment']
        dependencies = tree['dependencies']
        for dependency in dependencies:
            self.run_with_deps(dependency)

        logging.info("Launching deployment {}:{}".format(
            deployment.get('app_name'), deployment.get('image_tag')))
        self.run(deployment)

    def deploy(self, d):
        app_name = d['app_name']
        try:
            self.stop(app_name)
            self.rm(app_name)
        except Exception as e:
            logging.warn(e)
        self.run(d)
        
    def run(self, d):
        app_name = d['app_name']
        image_id = '%s/%s:%s' % (self.registry_user, app_name, d['image_tag'])
        status_url = 'http://%s:%s/%s' % (self.host, d['status_port'], d['status_endpoint'])
        
        mapped_ports = d.get('mapped_ports')
        mapped_volumes = d.get('mapped_volumes')
        
        env_vars = d.get('environment_variables')
        linked_apps = d.get('links')
        linked_volumes = d.get('volumes')
        
        ports = []
        port_bindings = {}
        if mapped_ports:
            port_bindings = dict([[int(p) for p in pm.split(':')] for pm in mapped_ports])
            ports = port_bindings.keys()

        volumes = []
        volume_bindings = {}
        if mapped_volumes:
            mv = dict([vm.split(':') for vm in mapped_volumes])
            volume_bindings = dict([(container_volume, {'bind':mv[container_volume]}) for container_volume in mv])
            volumes = mv.values()

        volumes_from = []
        if linked_volumes:
            volumes_from = [lv['app_name'] for lv in linked_volumes]

        links = {}
        if linked_apps:
            links = dict([(la['app_name'], la['app_name']) for la in linked_apps])

        c = None
        container = None
        kwargs = {
            'image': image_id,
            'name': app_name,
            'ports': ports,
            'volumes': volumes,
            'volumes_from': volumes_from,
            'environment': env_vars,
            'host_config': docker.utils.create_host_config(
                port_bindings=port_bindings,
                binds=volume_bindings,
                links=links
            )
        }
        
        try:
            container = self._client_request('create_container', **kwargs)
            self.start_container(container)
        except docker.errors.APIError as e:
            if e.message.response.status_code == 404:
                logging.warn('container not found locally, pulling')
                self._client_request('pull', image_id)
                container = self.create_container(**kwargs)
                self.start_container(container)
            else:
                raise e
