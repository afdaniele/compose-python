from types import SimpleNamespace

from .logger import logger
from .utils import check_valid_argument_value
from .exceptions import APIError


class APINamespace(SimpleNamespace):

    def __init__(self, **kwargs):
        super(APINamespace, self).__init__(**kwargs)

    def _has(self, service):
        return service in self.__dict__

    def __getattr__(self, item):
        if not item.startswith('__') and item not in self.__dict__:
            logger.error(
                "API service '{}' not found. ".format(item) +
                "Either such service does not exist or your API Application does not have access."
            )
            return ServiceProxy(None, item)
        # ---
        return super(APINamespace, self).__getattr__(item)


class ServiceProxy(SimpleNamespace):

    def __init__(self, compose, service_name, **kwargs):
        self._compose = compose
        self._service_name = service_name
        super(ServiceProxy, self).__init__(**kwargs)

    def _register_action(self, action_name, action_data):
        setattr(self, action_name, ActionProxy(self, action_name, action_data))

    def _execute(self, action_name, arguments=None):
        if self._compose:
            return self._compose._get(self._service_name, action_name, arguments)

    def __getattr__(self, item):
        if not item.startswith('__') and item not in self.__dict__:
            logger.error(
                "API action '{}/{}' not found. ".format(self._service_name, item) +
                "Either such action does not exist or your API Application does not have access."
            )
            return ActionProxy(self, item, dict(), fake=True)
        # ---
        return super(ServiceProxy, self).__getattr__(item)


class ActionProxy:

    def __init__(self, service, action_name, action_data, fake=False):
        self._service = service
        self._action_name = action_name
        self._action_data = action_data
        self._fake = fake

    def __call__(self, **kwargs):
        # check arguments
        self._check_arguments(kwargs)
        # call API
        success, data, msg = self._execute(**kwargs)
        # raise if error
        if not success:
            raise APIError(msg)
        # ---
        return data

    def _execute(self, **kwargs):
        return self._service._execute(self._action_name, arguments=kwargs)

    def _check_arguments(self, arguments):
        # get parameters lists
        mandatory_params = {}
        optional_params = {}
        if 'parameters' in self._action_data and 'mandatory' in self._action_data['parameters']:
            mandatory_params = self._action_data['parameters']['mandatory']
        if 'parameters' in self._action_data and 'optional' in self._action_data['parameters']:
            optional_params = self._action_data['parameters']['optional']
        # make sure all mandatory arguments are provided
        for key, parameter in mandatory_params.items():
            if key not in arguments:
                raise ValueError("The argument '{}' is mandatory".format(key))
            # validate argument value against API specifications
            check_valid_argument_value(key, parameter, arguments[key])
        # check optional arguments
        for key, value in arguments.items():
            # we checked mandatory args already
            if key in mandatory_params:
                continue
            # warn for extra arguments
            if key not in optional_params:
                logger.warn("The argument '{}' is not expected".format(key))
                continue
            # validate argument value against API specifications
            check_valid_argument_value(key, optional_params[key], arguments[key])
