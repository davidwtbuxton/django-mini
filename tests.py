from __future__ import with_statement
import unittest
from mock import MagicMock, Mock, patch, call
from optparse import OptionParser
from djangomini import (add_app_name, make_parser, parse_django_args, parse_args,
    settings_name, settings_value, _parse_rfc1738_args, parse_database_string,
    main, configure_urlconf, make_urlpatterns, configure_settings,
    make_admin_urlpatterns, DJANGO_SETTINGS, ADMIN_APPS)


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
        add_app_name(None, '--app', 'test:prefix', self.parser)
        self.assertEqual(self.parser.values.apps, [('test', 'prefix')])

    def test_without_prefix(self):
        add_app_name(None, '--app', 'test', self.parser)
        self.assertEqual(self.parser.values.apps, [('test', '')])


class ParsingTests(BaseTest):
    def test_make_parser(self):
        self.assertTrue(isinstance(make_parser(), OptionParser))

    def test_parse_args(self):
        argv = '--admin -d sqlite:///example.db -a app1 --extra=1 test'.split()
        opts, django_opts, args = parse_args(argv)
        
        self.assertEqual(opts.admin, True)
        self.assertEqual(opts.database, 'sqlite:///example.db')
        self.assertEqual(opts.apps, [('app1', '')])
        self.assertEqual(django_opts, {'EXTRA': 1})
        self.assertEqual(args, ['test'])

    def test_parse_django_args(self):
        argv = '--option a --other-option b arg1 arg2 --extra c'.split()
        options, remainder = parse_django_args(argv)
        self.assertEqual(options, {'OPTION': 'a', 'OTHER_OPTION': 'b', 'EXTRA': 'c'})
        self.assertEqual(remainder, ['arg1', 'arg2'])

    def test_settings_name(self):
        tests = [
            ('name', 'NAME'),
            ('with-underscore', 'WITH_UNDERSCORE'),
            ('--name', 'NAME'),
        ]
        
        for value, expected in tests:
            self.assertEqual(settings_name(value), expected)

    def test_settings_value(self):
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
            self.assertEqual(settings_value(value), expected)

    def test_parse_rfc1738_args(self):
        tests = [
            ('sqlite:///:memory:', {'name': 'sqlite', 'database': ':memory:',
                'username': None, 'host': '', 'query': None, 'password': None,
                'port': None,}),
        ]
        
        for value, expected in tests:
            self.assertEqual(_parse_rfc1738_args(value), expected)

    def test_parse_database_string(self):
        tests = [
            ('sqlite:///:memory:', {'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:', 'HOST': '', 'PASSWORD': None, 'PORT': None,
                'USER': None,}),
            ('/var/run/db/django.sqlite', {'ENGINE': 'django.db.backends.sqlite3',
                'NAME': '/var/run/db/django.sqlite', 'HOST': '', 'PASSWORD': None,
                'PORT': None, 'USER': None,}),
        ]
        
        for value, expected in tests:
            self.assertEqual(parse_database_string(value), expected)


class ConfigureDjangoTests(BaseTest):
    @patch('django.conf.settings')
    def test_configure_urlconf(self, settings):
        patterns = [(r'^test/', 'myapp.views.test')]
        configure_urlconf(patterns)
        
        self.assertEqual(settings.ROOT_URLCONF, tuple(patterns))

    @patch('django.conf.settings')
    def test_configure_settings(self, settings):
        settings_dict = {'DEBUG': True, 'TEST': 'test'}
        configure_settings(settings_dict)
        self.assertEqual(settings.configure.call_args, ((), settings_dict))


class MakeURLPatternsTests(BaseTest):
    @patch('django.conf.urls.import_module')
    def test_make_urlpatterns(self, import_module):
        app_map = [('app1', ''), ('app2', 'prefix')]
        result = make_urlpatterns(app_map)
        
        import_module.assert_has_calls([call('app1.urls'), call('app2.urls')])
        from django.conf.urls import RegexURLResolver

        for pattern in result:
            self.assertTrue(isinstance(pattern, RegexURLResolver))
    
    def test_make_admin_urlpatterns(self):
        from django.conf.urls import RegexURLResolver

        configure_settings({'INSTALLED_APPS': ADMIN_APPS})
        result = make_admin_urlpatterns()

        for pattern in result:
            self.assertTrue(isinstance(pattern, RegexURLResolver))


class MainTests(BaseTest):
    @patch('django.conf.urls.import_module')
    @patch('djangomini.call_command')
    def test_main_admin(self, call_command, import_module):
        from django.conf import settings
        
        argv = 'django-mini --admin runserver'.split()
        main(argv)
        
        call_command.assert_called_once_with('runserver')
        self.assertEqual(settings.INSTALLED_APPS, ADMIN_APPS)
    
    @patch('django.conf.urls.import_module')
    @patch('djangomini.execute_from_command_line')
    def test_main_admin(self, call_command, import_module):
        from django.conf import settings
        argv = 'django-mini --admin --staticfiles runserver'.split()
        main(argv)

        call_command.assert_called_once_with(['django-mini', 'runserver'])
        self.assertTrue('django.contrib.staticfiles' in settings.INSTALLED_APPS)

    @patch('django.conf.urls.import_module')
    @patch('django.utils.importlib.import_module')
    @patch('djangomini.execute_from_command_line')
    def test_main_full(self, call_command, import_module, import_module2):
        from django.conf import settings
        argv = ('django-mini --admin --staticfiles -a app1 --app app2 runserver'
                ' --database sqlite:////var/run/db.sqlite --static-url /cdn/'
                ).split()

        main(argv)

        call_command.assert_called_once_with(['django-mini', 'runserver'])
        apps = ['django.contrib.staticfiles', 'django.contrib.admin', 'app1', 'app2']
        for app in apps:
            self.assertTrue(app in settings.INSTALLED_APPS)
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(settings.DATABASES['default']['NAME'], '/var/run/db.sqlite')
        self.assertEqual(settings.STATIC_URL, '/cdn/')


if __name__ == "__main__":
    unittest.main()
