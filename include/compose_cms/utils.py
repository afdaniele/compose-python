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


def compile_query_string(arguments):
    return '&'.join(map(lambda e: '%s=%s' % e, arguments.items()))


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
