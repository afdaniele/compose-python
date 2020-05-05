import os
from setuptools import setup, find_packages

# :==> Fill in your project data here
version = '0.1.3'
library_name = 'compose_cms'
library_webpage = 'https://github.com/afdaniele/compose-python'
maintainer = 'Andrea F. Daniele'
maintainer_email = 'afdaniele@ttic.edu'
short_description = 'Python library for communicating with a \\compose\\ instance'
full_description = """
\\compose\\ (http://compose.afdaniele.com) is a CMS (Content Management System) platform written 
in PHP that provides functionalities for fast development of web applications on Linux servers.

This library provides an easy way of communicating with the REST API on an instance of \\compose\\.
"""
# <==: Fill in your project data here

# read project dependencies
dependencies_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dependencies.txt')
with open(dependencies_file, 'rt') as fin:
    dependencies = list(filter(lambda line: not line.startswith('#'), fin.read().splitlines()))

# compile description
underline = '=' * (len(library_name) + len(short_description) + 2)
description = """
{name}: {short}
{underline}

{long}
""".format(name=library_name, short=short_description, long=full_description, underline=underline)

# setup package
setup(name=library_name,
      author=maintainer,
      author_email=maintainer_email,
      url=library_webpage,
      install_requires=dependencies,
      package_dir={"": "include"},
      packages=find_packages('./include'),
      long_description=description,
      version=version,
      include_package_data=True)
