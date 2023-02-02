import os
import shutil
import json
import re
import copy
import glob

from compose_cms.utils import compose_type_to_python_type, ComposeObject, ComposeSchema


class __NOTFOUND__:
    pass


class Compose:

    def __init__(self, path=None, userdata=None):
        self._path = path or os.environ.get('COMPOSE_DIR', '/var/www/html/')
        self._system_dir = os.path.join(self._path, 'public_html', 'system')
        self._userdata = userdata or os.environ.get('COMPOSE_USERDATA_DIR',
                                                    os.path.join(self._system_dir, 'user-data'))

    @property
    def path(self):
        return self._path

    @property
    def userdata(self):
        return self._userdata

    @property
    def packages(self):
        packages = []
        paths = [
            os.path.join(self._path, 'public_html', 'system', 'packages', '*'),
            os.path.join(self._userdata, 'packages', '*')
        ]
        for path in paths:
            packages.extend([os.path.basename(p) for p in glob.glob(path) if os.path.isdir(p)])
        return packages

    def package(self, name):
        if len(name.strip()) <= 0:
            raise ValueError('Invalid package name "{}"'.format(name))
        paths = [
            os.path.join(self._path, 'public_html', 'system', 'packages', name),
            os.path.join(self._userdata, 'packages', name)
        ]
        for path in paths:
            if os.path.isdir(path):
                return ComposePackage(name, path, self)
        raise ValueError('Package {} not found'.format(name))

    def database(self, package, database):
        path = os.path.join(self._userdata, 'databases', package, database)
        return ComposeDatabase(path, self.package(package))


class ComposePackage:

    def __init__(self, name, path, compose):
        self._name = name
        self._path = path
        self._compose = compose

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def compose(self):
        return self._compose

    @property
    def enabled(self):
        db = self.compose.database('core', 'disabled_packages')
        return not db.key_exists(self.name)

    @property
    def pages(self):
        page_dir_pattern = os.path.join(self.path, 'pages', '*')
        return [os.path.basename(p) for p in glob.glob(page_dir_pattern) if os.path.isdir(p)]

    def page(self, name):
        return ComposePage(name, self)

    def configuration(self):
        return ComposePackageConfiguration(self)

    def enable(self):
        db = self.compose.database('core', 'disabled_packages')
        if db.key_exists(self.name):
            db.delete(self.name)

    def disable(self):
        db = self.compose.database('core', 'disabled_packages')
        db.write(self.name, [])


class ComposePage:

    def __init__(self, name, package):
        if len(name.strip()) <= 0:
            raise ValueError('Invalid page name "{}"'.format(name))
        self._name = name
        self._package = package
        self._compose = self._package.compose
        self._path = os.path.join(self.package.path, 'pages', name)
        if not os.path.isdir(self._path):
            raise ValueError('Page {}/{} not found'.format(self._package.name, name))

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def package(self):
        return self._package

    @property
    def compose(self):
        return self._compose

    @property
    def enabled(self):
        db = self.compose.database('core', 'disabled_pages')
        key = '{}__{}'.format(self.package.name, self.name)
        return not db.key_exists(key)

    def enable(self):
        db = self.compose.database('core', 'disabled_pages')
        key = '{}__{}'.format(self.package.name, self.name)
        if db.key_exists(key):
            db.delete(key)

    def disable(self):
        db = self.compose.database('core', 'disabled_pages')
        key = '{}__{}'.format(self.package.name, self.name)
        db.write(key, [])


class ComposePackageConfiguration:

    def __init__(self, package):
        self._package = package
        self._compose = self._package.compose
        self._schema = self._get_schema()

    @property
    def package(self):
        return self._package

    @property
    def compose(self):
        return self._compose

    @property
    def schema(self):
        return copy.deepcopy(self._schema.as_dict())

    def configuration(self, default=None):
        db = self._db()
        if default is not None and not db.key_exists('content'):
            return default
        return ComposeObject(db.read('content'))

    def _get_schema(self):
        schema_filepath = os.path.join(self.package.path, 'configuration', 'schema.json')
        if not os.path.isfile(schema_filepath):
            raise ValueError('Configuration schema file not found. '
                             'The package is not configurable')
        schema = json.load(open(schema_filepath, 'rt'))
        return ComposeSchema(schema)

    def get(self, key):
        config = self.configuration()
        # get the default value
        try:
            default = self._schema['{}.default'.format(key)]
        except KeyError:
            raise KeyError('Package {} has no configuration key {}'.format(self.package.name, key))
        # try to get the custom value
        try:
            value = config[key]
            return value
        except KeyError:
            pass
        # ---
        return default

    def set(self, key, value):
        # get the parameter type
        try:
            param_type = self._schema['{}.type'.format(key)]
        except KeyError:
            raise KeyError('Package {} has no configuration key {}'.format(self.package.name, key))
        # get current configuration
        config = self.configuration(ComposeObject())
        # format the value according to its type
        pclass = compose_type_to_python_type(param_type, default=str)
        value = pclass(value)
        # write new value to the DB
        config[key] = value
        db = self._db()
        db.write('content', config.as_dict())

    def _db(self):
        return self.compose.database(self.package.name, '__configuration__')


class ComposeDatabase:

    def __init__(self, path, package):
        self._path = path
        self._package = package

    @property
    def path(self):
        return self._path

    @property
    def package(self):
        return self._package

    @property
    def compose(self):
        return self._package.compose

    def read(self, key):
        self._key_exists_or_error(key)
        db_file = self._key_to_db_file(key)
        res = json.load(open(db_file, 'rt'))
        return ComposeObject(res['_data'])

    def write(self, key, data):
        db_file = self._key_to_db_file(key)
        db_dir = os.path.dirname(db_file)
        os.makedirs(db_dir, 0o775, exist_ok=True)
        json_str = json.dumps(
            {
                '_data': data,
                '_metadata': {}
            },
            sort_keys=True,
            indent=4
        )
        with open(db_file, 'wt') as fout:
            fout.write(json_str)

    def delete(self, key):
        self._key_exists_or_error(key)
        db_file = self._key_to_db_file(key)
        os.remove(db_file)

    def key_exists(self, key):
        db_file = self._key_to_db_file(key)
        return os.path.isfile(db_file)

    def list_keys(self):
        db_file_pattern = os.path.join(self._path, '*.json')
        return list(map(lambda p: os.path.basename(p)[:-5], glob.glob(db_file_pattern)))

    def size(self):
        return len(self.list_keys())

    def key_size(self, key):
        self._key_exists_or_error(key)
        db_file = self._key_to_db_file(key)
        return os.path.getsize(db_file)

    def is_writable(self, key):
        db_file = self._key_to_db_file(key)
        with open(db_file, "a") as fout:
            return fout.writable()

    @staticmethod
    def database_exists(package, database, userdata=None):
        db_dir = ComposeDatabase._sget_db_dir(package, database, userdata)
        return os.path.isdir(db_dir)

    @staticmethod
    def list_dbs(package, userdata=None):
        db_dir_pattern = ComposeDatabase._sget_db_dir(package, '*', userdata)
        return list(map(lambda p: os.path.basename(p), glob.glob(db_dir_pattern)))

    @staticmethod
    def delete_db(package, database, userdata=None):
        db_dir = ComposeDatabase._sget_db_dir(package, database, userdata)
        shutil.rmtree(db_dir)

    def _get_db_dir(self, database):
        return os.path.join(self.path, database)

    @staticmethod
    def _sget_db_dir(package, database, userdata=None):
        userdata = userdata or os.environ.get('COMPOSE_USERDATA_DIR', '/user-data')
        return os.path.join(userdata, 'databases', package, database)

    @staticmethod
    def _safe_key(key):
        return Utils.string_to_valid_filename(key)

    def _key_to_db_file(self, key):
        key = self._safe_key(key)
        return os.path.join(self._path, key + '.json')

    def _key_exists_or_error(self, key):
        if not self.key_exists(key):
            raise ValueError('The key {} does not exists'.format(key))


class Utils:

    @staticmethod
    def string_to_valid_filename(s: str):
        # lowercase
        s = s.lower()
        # replace more than one space to underscore
        s = re.sub(' +', '_', s)
        # convert any single space to underscrore
        s = s.replace(' ', '_')
        # remove non alpha numeric characters
        s = re.sub('[^A-Za-z0-9_]', '', s)
        # return sanitized string
        return s
