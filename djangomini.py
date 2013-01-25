#/usr/bin/env python
import sys
import optparse
import os
import string
import re
import types
import urllib
from django.utils.crypto import get_random_string
from django.core.exceptions import ImproperlyConfigured
from django.core.management import execute_from_command_line


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
    'mysql': 'django.db.backend.mysql',
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


class DjangoOptionParser(optparse.OptionParser):
    """Extends OptionParser to treat any unknown long option as a Django
    settings variable with a value. '--foo bar' -> 'FOO=bar'.
    """
    # We need to catch any unknown long option and create an Option for it.
    def _match_long_opt(self, opt):
        try:
            optparse.OptionParser._match_long_opt(self, opt)
        except optparse.BadOptionError:
            self.add_option(opt, action='callback', dest='django', default={},
                type='string', callback=add_django_option)
            return opt
    # Probably need to suppress these options in the help message.


def add_django_option(option, opt_str, value, parser):
    name = settings_name(value)
    value = settings_value(value)
    parser.values.django[name] = value


def add_app_name(option, opt_str, value, parser):
    """Call-back for the --app option and OptionParser."""
    name, sep, prefix = value.partition(':')
    parser.values.apps.append((name, prefix))


def make_parser():
    parser = optparse.OptionParser()
    parser.disable_interspersed_args()
    parser.add_option('-a', '--app', action='callback', dest='apps', default=[],
        type='string', callback=add_app_name)
    parser.add_option('-d', '--database', default='sqlite:///:memory:')
    parser.add_option('--admin', action='store_true', default=False)
    parser.add_option('--staticfiles', action='store_true', default=False)

    return parser


def parse_args(argv):
    opts, args = make_parser().parse_args(argv)

    return opts, opts.django, args


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

    if options.staticfiles:
        apps.append('django.contrib.staticfiles')

    settings['INSTALLED_APPS'] = apps
    settings['DATABASES'] = {'default': parse_database_string(options.database)}
    configure_settings(settings)

    urlpatterns = make_urlpatterns(options.apps)
    if options.admin:
        urlpatterns += make_admin_urlpatterns()

    configure_urlconf(urlpatterns)
    execute_from_command_line(['django-mini'] + arguments)


def configure_urlconf(patterns):
    from django.conf import settings

    if not patterns:
        raise ImproperlyConfigured('An app or admin is required.')

    # Has to be hashable or a string naming a module.
    settings.ROOT_URLCONF = tuple(patterns)


def configure_settings(kwargs):
    from django.conf import settings

    settings.configure(**kwargs)


def make_urlpatterns(app_map):
    from django.conf.urls import patterns, include, url

    urls = []
    for app, prefix in app_map:
        prefix = r'^%s/' % prefix if prefix else r'^'
        urls.append(url(prefix, include('%s.urls' % app)))

    return patterns('', *urls)


def make_admin_urlpatterns():
    from django.conf.urls import patterns, include, url
    from django.contrib import admin

    admin.autodiscover()
    return patterns('', url(r'^admin/', include(admin.site.urls)))


if __name__ == "__main__":
    main(sys.argv)
