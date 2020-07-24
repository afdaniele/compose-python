import re

ARGUMENT_TYPE_TO_PY_TYPE = {
    'text': (str, lambda s: True, 'Free text. Can contain letters, numbers, symbols, etc..'),
    'alphabetic': (str, lambda s: re.match('[a-zA-Z]+', s) is not None,
                   'Alphabetic string. Contains letters only.'),
    'alphanumeric': (str, lambda s: re.match('[a-zA-Z0-9]+', s) is not None,
                     'Alphanumeric string. Can contain letters and numbers.'),
    'numeric': (int, lambda v: v >= 0, 'A positive integer'),
    'float': (float, lambda v: True, 'A floating-point number'),
    'boolean': (bool, lambda v: True, 'Boolean values'),
    'enum': (object, lambda v: True, 'Enum values')
}


def compose_type_to_python_type(compose_type, default=None):
    if compose_type not in ARGUMENT_TYPE_TO_PY_TYPE:
        if default is None:
            raise ValueError('Compose type {} not recognized'.format(compose_type))
        return default
    pclass, _, _ = ARGUMENT_TYPE_TO_PY_TYPE[compose_type]
    if pclass == object:
        return str
    return pclass


def check_valid_argument_value(param_name, param_info, value):
    param_type = param_info['type']
    param_length = param_info['length'] if 'length' in param_info else None
    param_values = param_info['values'] if 'values' in param_info else None
    # ---
    if param_type not in ARGUMENT_TYPE_TO_PY_TYPE:
        raise ValueError("Value for API argument '{}' of type '{}' is not valid".format(
            param_name, param_type))
    # ---
    pclass, validator, description = ARGUMENT_TYPE_TO_PY_TYPE[param_type]
    # validate value type
    if not isinstance(value, pclass):
        raise ValueError(
            "API argument '{}' of type '{}' expects value of type '{}', got '{}' instead".format(
                param_name, param_type, pclass.__name__, value.__class__.__name__))
    # validate value
    if not validator(value):
        raise ValueError(
            "Value '{}' for API argument '{}' of type '{}' is not valid. Expected: {}".format(
                str(value), param_name, param_type, description))
    # validate length
    if param_length is not None and len(str(value)) != param_length:
        raise ValueError(
            "Value for API argument '{}' of type '{}' is expected to be of length {}".format(
                param_name, param_type, param_length))
    # validate values
    if param_values is not None and value not in param_values:
        raise ValueError(
            "Value for API argument '{}' of type '{}' is expected to be one of {}".format(
                param_name, param_type, str(param_values)))


class ComposeObject(dict):

    def _cursor_(self, item, create=False):
        ns = item.lstrip('/').split('/')
        res = self
        for cur in ns[:-1]:
            if isinstance(res, dict) and cur not in res:
                if create:
                    res[cur] = dict()
                else:
                    raise KeyError('Key not found: {}'.format(item))
            if isinstance(res, list):
                if (int(cur) < 0 or int(cur) > len(res)) or (int(cur) == len(res) and not create):
                    raise KeyError('Index {} out of range for list of {} elements'.format(
                        item, len(res)))
                if create:
                    res.append(dict())
            res = self._type_(res).__getitem__(res, cur)
        if isinstance(res, dict) and ns[-1] not in res and not create:
            raise KeyError('Key not found: {}'.format(item))
        return res, ns[-1]

    def __getitem__(self, item):
        cursor, tip = self._cursor_(item)
        return self._type_(cursor).__getitem__(cursor, tip)

    def __setitem__(self, key, value):
        cursor, tip = self._cursor_(key, create=True)
        return self._type_(cursor).__setitem__(cursor, tip, value)

    def as_dict(self):
        return dict(self.items())

    @staticmethod
    def _type_(item):
        if isinstance(item, dict):
            return dict
        if isinstance(item, list):
            return list
        return type(item)


class ComposeSchema(ComposeObject):

    def __getitem__(self, item: str):
        key = self._key_(item)
        return super(ComposeSchema, self).__getitem__(key)

    def __setitem__(self, key, value):
        key = self._key_(key)
        return super(ComposeSchema, self).__setitem__(key, value)

    @staticmethod
    def _key_(key):
        key = '/' + key.lstrip('/')
        key = key.replace('/', '/_data/')
        key = key.replace('.', '/')
        return key
