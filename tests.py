#!/usr/bin/env python
from __future__ import with_statement
from mock import MagicMock, Mock, patch, call
from optparse import OptionParser
import django
import djangomini
import unittest


django_13 = django.VERSION[:2] < (1, 4)
url_import_patch = 'django.core.urlresolvers.import_module' if django_13 else 'django.conf.urls.import_module'


class BaseTest(unittest.TestCase):
    def setUp(self):
        import django.conf

        self._original_settings = django.conf.settings
        django.conf.settings = django.conf.LazySettings()

    def tearDown(self):
        import django.conf

        django.conf.settings = self._original_settings


class AddAppNameTests(BaseTest):
    def setUp(self):
        super(AddAppNameTests, self).setUp()
        self.parser = Mock()
        self.parser.values.apps = []

    def test_with_prefix(self):
        djangomini.add_app_name(None, '--app', 'test:prefix', self.parser)
        self.assertEqual(self.parser.values.apps, [('test', 'prefix')])

    def test_without_prefix(self):
        djangomini.add_app_name(None, '--app', 'test', self.parser)
        self.assertEqual(self.parser.values.apps, [('test', '')])


class ParsingArgumentsTests(BaseTest):
    def test_make_parser(self):
        self.assertTrue(isinstance(djangomini.make_parser(), OptionParser))

    def test_default_args(self):
        opts, django_opts, args = djangomini.parse_args(['test'])

        expected = {
            'admin': False,
            'persisting': False,
            'apps': [],
            'database': 'sqlite:///:memory:',
            'debug_toolbar': False,
        }

        for option, value in expected.items():
            self.assertEqual(getattr(opts, option), value)

    def test_parse_args(self):
        # The key is the arg line, the value is a triple. First properties and
        # values of the opts, second the django_opts, last any positional args
        # that are passed through to Django.
        data = {
            '--admin -d sqlite:///example.db -a app1 --extra=1 test': (
                {'admin': True, 'database': 'sqlite:///example.db',
                    'apps': [('app1', '')]},
                {'EXTRA': 1},
                ['test'],
            ),
            '-a app1 --app app2:foo --installed-apps [\'bar\'] test': (
                {'admin': False, 'database': 'sqlite:///:memory:',
                    'apps': [('app1', ''), ('app2', 'foo')]},
                {'INSTALLED_APPS': ['bar']},
                ['test'],
            ),
            'syncdb --noinput --database=DATABASE': (
                {'admin': False, 'database': 'sqlite:///:memory:', 'apps': []},
                {},
                ['syncdb', '--noinput', '--database=DATABASE'],
            ),
            '--database=sqlite:///:memory: --foo bar test': (
                {'admin': False, 'database': 'sqlite:///:memory:',
                    'apps': [],},
                {'FOO': 'bar',},
                ['test'],
            ),
        }

        for line, expected in data.items():
            opts, django_opts, args = djangomini.parse_args(line.split(' '))

            for key, expected_value in expected[0].items():
                self.assertEqual(getattr(opts, key), expected_value)
            self.assertEqual(django_opts, expected[1])
            self.assertEqual(args, expected[2])

    def test_parse_help(self):
        # All these command lines should show the help.
        data = [
            '--help',
            '-d sqlite:///example.db --help',
            '-h',
        ]

        for line in data:
            self.assertRaises(SystemExit, djangomini.parse_args, line.split())

    def test_settings_name(self):
        # How extra argument flags get converted to Python names.
        tests = [
            ('name', 'NAME'),
            ('with-underscore', 'WITH_UNDERSCORE'),
            ('--name', 'NAME'),
            ('name--', 'NAME__'), # Trailing dash ain't my prob.
        ]

        for value, expected in tests:
            self.assertEqual(djangomini.settings_name(value), expected)

    def test_settings_value(self):
        # How extra argument values get converted to Python types.
        tests = [
            ('True', True),
            ('"string"', 'string'),
            ('["a", "b"]', ['a', 'b']),
            ('None', None),
            ('1', 1),
            ('0', 0),
            ('/test/', '/test/'),
        ]

        for value, expected in tests:
            self.assertEqual(djangomini.settings_value(value), expected)


class ParsingDatabaseStringTests(BaseTest):
    def test_parse_rfc1738_args(self):
        # Parsing database connection strings into their components.
        tests = [
            ('sqlite:///:memory:', {'name': 'sqlite', 'database': ':memory:',
                'username': None, 'host': '', 'query': None, 'password': None,
                'port': None,}),
            ('mysql://root@localhost/mydatabase?charset=utf8&use_unicode=0', {
                'name': 'mysql', 'database': 'mydatabase', 'username': 'root',
                'host': 'localhost', 'password': None, 'port': None,
                'query': {'charset': 'utf8', 'use_unicode': '0'},
                }),
            ('custom.backend.driver://localhost/mydatabase', {
                'name': 'custom.backend.driver', 'database': 'mydatabase',
                'username': None, 'host': 'localhost', 'password': None,
                'port': None, 'query': None,
                }),
        ]

        for value, expected in tests:
            self.assertEqual(djangomini._parse_rfc1738_args(value), expected)

    def test_parse_database_string(self):
        # Parsing database connection command line arguments into their
        # equivalent Django database specification.
        tests = [
            ('sqlite:///:memory:', {'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:', 'HOST': '', 'PASSWORD': '', 'PORT': '',
                'USER': '', 'OPTIONS': {},}),
            ('/var/run/db/django.sqlite', {'ENGINE': 'django.db.backends.sqlite3',
                'NAME': '/var/run/db/django.sqlite', 'HOST': '', 'PASSWORD': '',
                'PORT': '', 'USER': '', 'OPTIONS': {},}),
            ('postgresql://scott:tiger@localhost:5432/mydatabase', {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'mydatabase', 'HOST': 'localhost', 'PASSWORD': 'tiger',
                'PORT': '5432', 'USER': 'scott', 'OPTIONS': {},}),
            ('mysql://root@localhost/mydatabase?charset=utf8&use_unicode=0', {
                'ENGINE': 'django.db.backends.mysql', 'NAME': 'mydatabase',
                'HOST': 'localhost', 'PASSWORD': '', 'PORT': '',
                'USER': 'root', 'OPTIONS': {'charset': 'utf8', 'use_unicode': '0'},
                }),
            ('custom.backend.driver://localhost/mydatabase', {
                'ENGINE': 'custom.backend.driver', 'NAME': 'mydatabase',
                'HOST': 'localhost', 'PASSWORD': '', 'PORT': '', 'USER': '',
                'OPTIONS': {},
                }),

        ]

        for value, expected in tests:
            self.assertEqual(djangomini.parse_database_string(value), expected)


class ConfigureDjangoTests(BaseTest):
    @patch('django.conf.settings')
    def test_configure_urlconf(self, settings):
        # Check our built-in URL module is configured.
        patterns = [(r'^test/', 'myapp.views.test')]
        djangomini.configure_urlconf(patterns)

        self.assertEqual(settings.ROOT_URLCONF, djangomini._rooturlconf)

    @patch('django.conf.settings')
    def test_configure_settings(self, settings):
        # Check Django's configure settings machinery was called.
        settings_dict = {'DEBUG': True, 'TEST': 'test'}
        djangomini.configure_settings(settings_dict)
        self.assertEqual(settings.configure.call_args, ((), settings_dict))


class MakeURLPatternsTests(BaseTest):
    @patch(url_import_patch)
    def test_make_urlpatterns(self, import_module):
        # make_urlpatterns() result is an iterable of RegexURLResolver objects.
        app_map = [('app1', ''), ('app2', 'prefix')]
        result = djangomini.make_urlpatterns(app_map)

        # Django 1.3 the module gets imported only when a request comes in
        if not django_13:
            import_module.assert_has_calls([call('app1.urls'), call('app2.urls')])

        try:
            from django.conf.urls import RegexURLResolver
        except ImportError:
            # Django 1.3
            from django.core.urlresolvers import RegexURLResolver

        for pattern in result:
            self.assertTrue(isinstance(pattern, RegexURLResolver))

    def test_make_admin_urlpatterns(self):
        # make_admin_urlpatters() result is an iterable of RegexURLResolver
        # objects, although it relies on Django's settings to have been configured.
        try:
            from django.conf.urls import RegexURLResolver
        except ImportError:
            # Django 1.3
            from django.core.urlresolvers import RegexURLResolver

        settings = djangomini.add_custom_app('admin')
        djangomini.configure_settings(settings)
        result = djangomini.make_admin_urlpatterns()

        for pattern in result:
            self.assertTrue(isinstance(pattern, RegexURLResolver))


class MainTests(BaseTest):
    @patch(url_import_patch)
    @patch('django.core.management.execute_from_command_line')
    def test_main_admin2(self, execute_from_command_line, import_module):
        # main() calls Django's execute_from_command_line() to do the work.
        from django.conf import settings
        argv = 'django-mini --admin runserver'.split()
        djangomini.main(argv)

        execute_from_command_line.assert_called_once_with(['django-mini', 'runserver'])

    @patch(url_import_patch)
    @patch('django.utils.importlib.import_module')
    @patch('django.core.management.execute_from_command_line')
    def test_main_full(self, call_command, import_module, import_module2):
        # main() calls Django's execute_from_command_line(), full example.
        from django.conf import settings
        argv = ('django-mini --admin -a app1 --app app2'
                ' --database sqlite:////var/run/db.sqlite --static-url /cdn/'
                ' runserver --insecure 80'
                ).split()

        djangomini.main(argv)

        call_command.assert_called_once_with(['django-mini', 'runserver', '--insecure', '80'])
        apps = ['django.contrib.admin', 'app1', 'app2']
        for app in apps:
            self.assertTrue(app in settings.INSTALLED_APPS)
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(settings.DATABASES['default']['NAME'], '/var/run/db.sqlite')
        self.assertEqual(settings.STATIC_URL, '/cdn/')


class CustomAppsTests(BaseTest):
    def test_admin_app(self):
        # django.contrib.admin
        result = djangomini.add_custom_app('admin')
        self.assertTrue('django.contrib.admin' in result['INSTALLED_APPS'])

    def test_debug_toolbar_app(self):
        # django-debug-toolbar
        result = djangomini.add_custom_app('django-debug-toolbar')
        self.assertTrue('debug_toolbar' in result['INSTALLED_APPS'])

    def test_unknown_app(self):
        # add_custom_app() with an unknown name raises KeyError.
        self.assertRaises(KeyError, djangomini.add_custom_app, 'UNKNOWN')

    def test_returns_dict(self):
        # add_custom_app() returns {} if settings is omitted or None.
        result = djangomini.add_custom_app('admin', settings=None)
        self.assertTrue(isinstance(result, dict))

    def test_returns_settings(self):
        # add_custom_app() returns the same object if settings != None.
        settings = {}
        result = djangomini.add_custom_app('admin', settings=settings)
        self.assertTrue(result is settings)

    def test_settings_must_be_mapping(self):
        # add_custom_app() settings argument must me a mapping type.
        class SettingsType(object): pass
        settings = SettingsType()
        self.assertRaises(TypeError, djangomini.add_custom_app, 'admin', settings=settings)


if __name__ == "__main__":
    unittest.main()
