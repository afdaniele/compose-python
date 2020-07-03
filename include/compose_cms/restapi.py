import requests

from .exceptions import APIError
from .proxies import ServiceProxy, APINamespace


class ComposeRestAPI(object):

    _base_url = "%s://%s/web-api/%s/%s/%s/json"
    _services = []

    def __init__(self, host, app_id, app_secret, version='1.0', protocol='auto', interactive=False):
        self._hostname = host[:-1] if host[-1] == '/' else host
        self._version = version
        self._app_id = app_id
        self._app_secret = app_secret
        # define standard arguments
        self._arguments = {
            'app_id': self._app_id,
            'app_secret': self._app_secret
        }
        # create API namespace
        self.api = APINamespace(self)
        # check protocol value
        if protocol not in ['auto', 'http', 'https']:
            raise ValueError("The value of protocol must be one of ['auto', 'http', 'https']")
        # find protocol
        self._protocol = protocol if protocol != 'auto' else self._get_protocol()
        # load available endpoints (in interactive mode only)
        if interactive:
            self.reload_endpoints()

    def reload_endpoints(self):
        # remove all services
        for service_name in self._services:
            if self.api._has(service_name):
                delattr(self.api, service_name)
        # get new endpoints
        endpoints = self.endpoints()
        # parse info
        for endpoint in endpoints:
            # register service
            self._register_service(endpoint['service'])
            # create action proxy
            getattr(self.api, endpoint['service'])._register_action(endpoint['action'], endpoint)

    def endpoints(self):
        success, data, msg = self._get('api', 'app_info')
        # ---
        if success:
            return data['endpoints']
        # ---
        raise APIError('The API cannot be reached!')

    def is_endpoint_available(self, endpoint):
        endpoints = self.endpoints()
        if endpoints is None:
            return False
        return endpoint in [e['endpoint'] for e in endpoints]

    def _register_service(self, service_name):
        # create service proxy if it does not exist
        if not self.api._has(service_name):
            setattr(self.api, service_name, ServiceProxy(self, service_name))
            self._services.append(service_name)

    def _get(self, service, action, arguments=None, protocol=None):
        url = self._build_url(service, action, protocol)
        # call the RESTful API
        try:
            args = {**(arguments or {}), **self._arguments}
            res = requests.get(url, params=args).json()
        except (requests.exceptions.RequestException, ConnectionResetError, ValueError) as err:
            return False, None, str(err)
        # return result
        if res['code'] == 200:
            return True, res['data'], 'OK'
        # ---
        return False, None, res['message']

    def _build_url(self, service, action, protocol=None):
        protocol = protocol or self._protocol
        return self._base_url % (protocol, self._hostname, self._version, service, action)

    def _get_protocol(self):
        for proto in ['https', 'http']:
            success, _, _ = self._get('api', 'app_info', protocol=proto)
            if success:
                return proto
        raise APIError('The API cannot be reached!')
