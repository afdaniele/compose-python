import json


# This will monkey-patch json module when it's imported, so JSONEncoder.default() automatically
# checks for a special to_json() method and uses it to encode the object if found.


def _default(_, obj):
    # noinspection PyArgumentList
    return getattr(obj.__class__, "toJSON", _default.default)(obj)


_default.default = json.JSONEncoder().default
json.JSONEncoder.default = _default


__all__ = []
