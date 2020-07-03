import os
import shutil
import json
import re
import glob


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

    def page(self, name):
        return ComposePage(name, self, self._compose)

    def enable(self):
        db = self.compose.database('core', 'disabled_packages')
        if db.key_exists(self.name):
            db.delete(self.name)

    def disable(self):
        db = self.compose.database('core', 'disabled_packages')
        db.write(self.name, [])


class ComposePage:

    def __init__(self, name, package, compose):
        if len(name.strip()) <= 0:
            raise ValueError('Invalid page name "{}"'.format(name))
        self._name = name
        self._package = package
        self._compose = compose
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
        if self.key_exists(key):
            raise ValueError('The key {} does not exists'.format(key))
        db_file = self._key_to_db_file(key)
        res = json.load(open(db_file, 'rt'))
        return res['_data']

    def write(self, key, data):
        if self.key_exists(key):
            raise ValueError('The key {} does not exists'.format(key))
        db_file = self._key_to_db_file(key)
        json.dump({
            '_data': data,
            '_metadata': {}
        },
            open(db_file, 'wt')
        )

    def delete(self, key):
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
