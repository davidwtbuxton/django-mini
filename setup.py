from distutils.core import setup
from djangomini import __version__


setup(
    name = 'Django-mini',
    version = __version__,
    description = 'Admin tool for plug-able Django apps',
    author = 'David Buxton',
    author_email = 'david@gasmark6.com',
    py_modules = ['djangomini'],
    scripts = ['django-mini.py'],
)
