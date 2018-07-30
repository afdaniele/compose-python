import requests

class Compose(object):

    host = None
    version = None
    app_id = None
    app_secret = None
    base_url = "%s/web-api/%s/%s/%s/json?app_id=%s&app_secret=%s&%s"

    def __init__(self, host, version, app_id, app_secret):
        self.host = host[:-1] if host[-1] == '/' else host
        self.version = version
        self.app_id = app_id
        self.app_secret = app_secret
        # build app_info url
        url = self._build_url( 'api', 'app_info', [] )
        # try to connect and get the info
        response = requests.get(url)
        data = response.json()

        print data

    def endpoints(self): pass #TODO: lists all the endpoints this app has access to

    def _build_url(self, service, action, arguments):
        return self.base_url % (
            self.host,
            self.version,
            service,
            action,
            self.app_id,
            self.app_secret,
            ''
            # TODO: queryString here
        )


class ComposeServiceProxy(object):
    compose = None

class ComposeActionProxy(object):
    compose = None

#TODO: define service/action Proxyes so that we can call compose.service_name.action_name(<args>) and get back a Python dict
