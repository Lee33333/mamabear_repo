import docker
import requests
import logging

logging.basicConfig(level=logging.INFO)

class DockerWrapper(object):

    def __init__(self, docker_host, docker_port, config):
        self.host = docker_host
        self.port = docker_port
        self._tls_conf = docker.tls.TLSConfig(
            assert_hostname=False,
            verify=False,
            client_cert=(
                config.get('docker', 'client_cert'),
                config.get('docker', 'client_key')
            ))
        self._client = docker.Client(
            base_url='https://%s:%s' % (docker_host, docker_port),
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
            universe.append({
                'id': cid,
                'image_id': detail['Image'],
                'image_ref': info['Image'],
                'command': ' '.join(detail['Config']['Cmd']),
                'state': self._state_from_detail(detail['State']),
                'started_at': detail['State']['StartedAt'],
                'finished_at': detail['State']['FinishedAt']
            })
        return universe
            
    def ps(self, **kwargs):
        return self._client.containers(**kwargs)

    def inspect(self, container_id):
        return self._client.inspect_container(container_id)
        
    def logs(self, container_id, stderr=False, stdout=False, stream=False, tail=10):
        return self._client.logs(
            container_id, stderr=stderr, stdout=stdout, stream=stream, tail=tail)

    def pull(self, app_name):
        return self._client.pull(app_name)

    def rm(self, container_id):
        return self._client.remove_container(container_id)

    def stop(self, container_id):
        return self._client.stop(container_id)

    def run(self, app_name, image_id, mapped_ports=None, mapped_volumes=None):
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
            
        container = self._client.create_container(
            image=image_id,
            name=app_name,
            ports = ports,
            volumes = volumes,
            host_config=docker.utils.create_host_config(
                port_bindings=port_bindings,
                binds=volume_bindings
            )
        )
        return self._client.start(container=container.get('Id'))
