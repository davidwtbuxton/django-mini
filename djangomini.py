#/usr/bin/env python
from optparse import Option, OptionParser, BadOptionError
import hashlib
import logging
import imp
import os
import re
import string
import sys
import types
import urllib


logging.basicConfig(loglevel=logging.INFO)


try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

try:
    from urllib.parse import unquote_plus
except ImportError:
    from urllib import unquote_plus


__version__ = '0.5'
BACKENDS = {
    'postgresql': 'django.db.backends.postgresql_psycopg2',
    'mysql': 'django.db.backends.mysql',
    'sqlite': 'django.db.backends.sqlite3',
    'oracle': 'django.db.backends.oracle',
}
DJANGO_SETTINGS = {
    'DEBUG': True,
    'INTERNAL_IPS': ('127.0.0.1',),
    'STATIC_URL': '/static/',
    'STATIC_ROOT': 'static',
    'SITE_ID': 1,
}
DEFAULT_DATABASE = 'sqlite:///:memory:'
PERSISTING_DATABASE = 'sqlite:///djangomini.sqlite'
CUSTOM_APPS = {
    'admin': {
        'INSTALLED_APPS': [
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.admin',
            'django.contrib.staticfiles',
        ],
    },
    'django-debug-toolbar': {
        'MIDDLEWARE_CLASSES': ['debug_toolbar.middleware.DebugToolbarMiddleware'],
        'INTERNAL_IPS': ['127.0.0.1'],
        'INSTALLED_APPS': [
            'debug_toolbar',
            'django.contrib.staticfiles',
        ],
        'DEBUG': True,
    },
}
_rooturlconf = 'djangominiurlconf'


class DjangoOptionParser(OptionParser):
    """Extends OptionParser to treat any unknown long option as a Django
    settings variable with a value. '--foo bar' -> 'FOO=bar'.
    """
    # We need to catch any unknown long option and create an Option for it.
    def _match_long_opt(self, opt):
        try:
            return OptionParser._match_long_opt(self, opt)
        except BadOptionError:
            option = Option(opt, action='callback', dest='django',
                type='string', callback=add_django_option)
            # Adding the option straight in by-passes the help mechanism.
            self._long_opt[opt] = option
            return opt


def add_django_option(option, opt_str, value, parser):
    name = settings_name(opt_str)
    value = settings_value(value)
    if not hasattr(parser.values, 'django'):
        parser.values.django = {}
    parser.values.django[name] = value


def add_app_name(option, opt_str, value, parser):
    """Call-back for the --app option and OptionParser."""
    name, sep, prefix = value.partition(':')
    parser.values.apps.append((name, prefix))


def make_parser():
    parser = DjangoOptionParser(version='%prog ' + __version__,
        usage='usage: %prog [options] command')
    # Important! Makes it easy to pass options to the Django command.
    parser.disable_interspersed_args()
    parser.add_option('-a', '--app', action='callback', dest='apps', default=[],
        type='string', callback=add_app_name, metavar='APPNAME',
        help='add an app and its url patterns')
    parser.add_option('-d', '--database', default=DEFAULT_DATABASE,
        help='configure a database')
    parser.add_option('--admin', action='store_true', default=False,
        help="add Django's admin and its dependencies")
    parser.add_option('-p', '--persisting', default=False, action='store_true',
        help='use %s instead of an in-memory database' % PERSISTING_DATABASE)
    parser.add_option('--debug-toolbar', default=False, action='store_true',
        help='sets DEBUG=True and activates django-debug-toolbar if present')

    return parser


def parse_args(argv):
    parser = make_parser()
    opts, args = parser.parse_args(argv)
    django_opts = getattr(opts, 'django', {})

    return opts, django_opts, args


def settings_name(value):
    """Makes a capitalized name from an option flag."""
    return value.lstrip('-').replace('-', '_').upper()


def settings_value(value):
    """Returns the evaluated string."""
    try:
        return eval(value, {}, {})
    except (NameError, SyntaxError):
        return value


# Taken from SQLAlchemy.
def _parse_rfc1738_args(name):
    # Modified to permit dots in the engine name.
    pattern = re.compile(r'''
            (?P<name>[\w\.\+]+)://
            (?:
                (?P<username>[^:/]*)
                (?::(?P<password>[^/]*))?
            @)?
            (?:
                (?P<host>[^/:]*)
                (?::(?P<port>[^/]*))?
            )?
            (?:/(?P<database>.*))?
            ''', re.X)

    m = pattern.match(name)
    if m is not None:
        components = m.groupdict()
        if components['database'] is not None:
            tokens = components['database'].split('?', 2)
            components['database'] = tokens[0]
            query = (len(tokens) > 1 and dict(parse_qsl(tokens[1]))) or None
        else:
            query = None
        components['query'] = query

        if components['password'] is not None:
            components['password'] = unquote_plus(components['password'])

        return components
    else:
        raise ValueError(
            "Could not parse rfc1738 URL from string '%s'" % name)


def parse_database_string(value):
    """Parses a database connection string and returns a dictionary suitable
    for use in Django's DATABASES setting.

    A path string is interpreted as an sqlite database.
    """
    try:
        parts = _parse_rfc1738_args(value)
    except ValueError:
        parts = _parse_rfc1738_args('sqlite:///%s' % value)

    return {
        'ENGINE': BACKENDS.get(parts['name'], parts['name']),
        'NAME': parts['database'] or '',
        'HOST': parts['host'] or '',
        'PASSWORD': parts['password'] or '',
        'PORT': parts['port'] or '',
        'USER': parts['username'] or '',
        'OPTIONS': parts['query'] or {},
    }


def make_secret_key(options):
    """Returns a string for use as the SECRET_KEY setting."""
    db_string = options.database.encode('US-ASCII')
    return hashlib.md5(db_string).hexdigest()[:50]


def add_custom_app(name, settings=None):
    """Adds the necessary bits to a settings dictionary for a named app."""
    from django.conf import global_settings

    custom_settings = CUSTOM_APPS[name]

    # Check specifically against None so they can supply their own empty dict.
    if settings is None:
        settings = {}

    for key, custom_value in custom_settings.items():
        if isinstance(custom_value, (list, tuple)):
            if key in settings:
                existing = list(settings[key])
            else:
                existing = list(getattr(global_settings, key))

            for item in custom_value:
                if item not in existing:
                    existing.append(item)
            settings[key] = existing

        else:
            settings[key] = custom_value

    return settings


def main(argv):
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        err = sys.exc_info()[1]
        sys.stderr.write('%s.\nHave you installed Django?\n' % str(err))
        sys.exit(1)

    options, django_options, arguments = parse_args(argv[1:])
    settings = dict(DJANGO_SETTINGS)
    settings.update(django_options)

    # At least one argument, else we see Django's help instead of our own.
    if not arguments:
        make_parser().print_help()
        sys.exit(2)

    if options.persisting and (options.database == DEFAULT_DATABASE):
        options.database = PERSISTING_DATABASE

    settings['INSTALLED_APPS'] = [name for name, prefix in options.apps]
    settings['DATABASES'] = {'default': parse_database_string(options.database)}
    # Only set after the database has been set.
    settings.setdefault('SECRET_KEY', make_secret_key(options))

    if options.debug_toolbar:
        add_custom_app('django-debug-toolbar', settings)

    if options.admin:
        add_custom_app('admin', settings)

    configure_settings(settings)

    urlpatterns = make_urlpatterns(options.apps)
    if options.admin:
        # Force /admin/ first in the patterns.
        urlpatterns = make_admin_urlpatterns() + urlpatterns

    configure_urlconf(urlpatterns)
    execute_from_command_line(['django-mini'] + arguments)


def configure_urlconf(patterns):
    """Sets up Django's settings.ROOT_URLCONF patterns."""
    from django.conf import settings

    # Has to be hashable or a string naming a module.
    # Make a real module for compatibility.
    mod = imp.new_module(_rooturlconf)
    mod.urlpatterns = patterns
    sys.modules[_rooturlconf] = mod
    settings.ROOT_URLCONF = _rooturlconf


def configure_settings(kwargs):
    """Sets up Django's settings module."""
    from django.conf import settings

    settings.configure(**kwargs)


def make_urlpatterns(app_map):
    """Creates a new patterns() list from the list of (app, prefix) strings."""
    try:
        from django.conf.urls import patterns, include, url
    except ImportError:
        # Django 1.3
        from django.conf.urls.defaults import patterns, include, url

    urls = []
    for app, prefix in app_map:
        prefix = r'^%s/' % prefix if prefix else r'^'
        module = '%s.urls' % app
        try:
            urls.append(url(prefix, include(module)))
        except ImportError:
            logging.warn('Failed to add %r to URL patterns, moving on.', module)

    return patterns('', *urls)


def make_admin_urlpatterns():
    """Imports the default site admin instance and returns a patterns() list
    configured to serve it at /admin/.
    """
    try:
        from django.conf.urls import patterns, include, url
    except ImportError:
        # Django 1.3
        from django.conf.urls.defaults import patterns, include, url
    from django.contrib import admin

    admin.autodiscover()
    return patterns('', url(r'^admin/', include(admin.site.urls)))


if __name__ == "__main__":
    main(sys.argv)
