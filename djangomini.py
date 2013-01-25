#/usr/bin/env python
import sys
from optparse import Option, OptionParser, BadOptionError
import os
import string
import re
import types
import urllib
from django.utils.crypto import get_random_string
from django.core.exceptions import ImproperlyConfigured
from django.core.management import execute_from_command_line
import logging


logging.basicConfig(loglevel=logging.DEBUG)

try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

try:
    next
except NameError:
    next = lambda x: x.next()


__version__ = '0.1'
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
    'SECRET_KEY': get_random_string(50, string.printable[:80]),
}
ADMIN_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
)


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
    parser = DjangoOptionParser(version='%prog ' + __version__)
    # Important! Makes it easy to pass options to the Django command.
    parser.disable_interspersed_args()
    parser.add_option('-a', '--app', action='callback', dest='apps', default=[],
        type='string', callback=add_app_name, metavar='APPNAME')
    parser.add_option('-d', '--database', default='sqlite:///:memory:')
    parser.add_option('--admin', action='store_true', default=False)

    return parser


def parse_args(argv):
    parser = make_parser()
    opts, args = parser.parse_args(argv)
    django_opts = getattr(opts, 'django', {})

    # If you don't specify a command we require --admin or one --app.
    if not args and not (opts.admin or opts.apps):
        parser.error('--admin or --app=APPNAME is required')

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
    pattern = re.compile(r'''
            (?P<name>[\w\+]+)://
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
            # Py2K
            if query is not None:
                query = dict((k.encode('ascii'), query[k]) for k in query)
            # end Py2K
        else:
            query = None
        components['query'] = query

        if components['password'] is not None:
            components['password'] = \
                urllib.unquote_plus(components['password'])

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
        'NAME': parts['database'],
        'HOST': parts['host'],
        'PASSWORD': parts['password'],
        'PORT': parts['port'],
        'USER': parts['username'],
    }


def main(argv):
    options, django_options, arguments = parse_args(argv[1:])
    settings = dict(DJANGO_SETTINGS)
    settings.update(django_options)

    apps = [name for name, prefix in options.apps]
    if options.admin:
        apps.extend(name for name in ADMIN_APPS if name not in apps)

    settings['INSTALLED_APPS'] = apps
    settings['DATABASES'] = {'default': parse_database_string(options.database)}
    configure_settings(settings)

    urlpatterns = make_urlpatterns(options.apps)
    if options.admin:
        urlpatterns += make_admin_urlpatterns()

    configure_urlconf(urlpatterns)
    execute_from_command_line(['django-mini'] + arguments)


def configure_urlconf(patterns):
    """Sets up Django's settings.ROOT_URLCONF patterns."""
    from django.conf import settings

    if not patterns:
        raise ImproperlyConfigured('--app or --admin is required.')

    # Has to be hashable or a string naming a module.
    settings.ROOT_URLCONF = tuple(patterns)


def configure_settings(kwargs):
    """Sets up Django's settings module."""
    from django.conf import settings

    settings.configure(**kwargs)


def make_urlpatterns(app_map):
    """Creates a new patterns() list from the list of (app, prefix) strings."""
    from django.conf.urls import patterns, include, url

    urls = []
    for app, prefix in app_map:
        prefix = r'^%s/' % prefix if prefix else r'^'
        urls.append(url(prefix, include('%s.urls' % app)))

    return patterns('', *urls)


def make_admin_urlpatterns():
    """Imports the default site admin instance and returns a patterns() list
    configured to serve it at /admin/.
    """
    from django.conf.urls import patterns, include, url
    from django.contrib import admin

    admin.autodiscover()
    return patterns('', url(r'^admin/', include(admin.site.urls)))


if __name__ == "__main__":
    main(sys.argv)
