import requests

class Compose(object):
    _host = None
    _version = None
    _app_id = None
    _app_secret = None
    _base_url = "%s/web-api/%s/%s/%s/json?app_id=%s&app_secret=%s&%s"

    def __init__(self, host, app_id, app_secret, version='1.0'):
        self._host = host[:-1] if host[-1] == '/' else host
        self._version = version
        self._app_id = app_id
        self._app_secret = app_secret
        # get API info
        endpoints = self.endpoints()
        # parse info
        for endpoint in endpoints:
            service_name = endpoint['service']
            action_name = endpoint['action']
            # register service
            self._register_service(service_name)
            # create action proxy
            self.__dict__[service_name]._register_action(action_name, endpoint)

    def endpoints(self):
        info = self._get('api', 'app_info')
        return info['endpoints']

    def _register_service(self, service_name):
        # create service proxy if it does not exist
        if service_name not in self.__dict__:
            self.__dict__[service_name] = ComposeServiceProxy(self, service_name)

    def _get(self, service, action, arguments={}):
        url = self._build_url(service, action, arguments)
        # call the RESTful API
        response = requests.get(url)
        data = response.json()
        # return result
        if data['code'] == 200:
            return data['data']
        return None

    def _build_url(self, service, action, arguments):
        return self._base_url % (
            self._host,
            self._version,
            service,
            action,
            self._app_id,
            self._app_secret,
            self._query_string(arguments)
        )

    def _query_string(self, arguments):
        return '&'.join( [ '%s=%s' % (k,v) for k, v in arguments.items() ] )


class ComposeServiceProxy(object):
    _compose = None
    _service_name = None

    def __init__(self, compose, service_name):
        self._compose = compose
        self._service_name = service_name

    def _register_action(self, action_name, action_data):
        self.__dict__[action_name] = ComposeActionProxy(self, action_name, action_data)

    def _execute(self, action_name, arguments={}):
        return self._compose._get(self._service_name, action_name, arguments)


class ComposeActionProxy(object):
    _service = None
    _action_name = None
    _action_data = None

    def __init__(self, service, action_name, action_data):
        self._service = service
        self._action_name = action_name
        self._action_data = action_data

    def __call__(self, arguments={}):
        #TODO: check arguments
        return self._execute( arguments )

    def _execute(self, arguments={}):
        return self._service._execute(self._action_name, arguments)
