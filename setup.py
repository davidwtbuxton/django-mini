from distutils.core import setup
from djangomini import __version__
import os


read = lambda x: open(os.path.join(os.path.dirname(__file__), x)).read()


setup(
    name = 'django-mini',
    version = __version__,
    author = 'David Buxton',
    author_email = 'david@gasmark6.com',
    url = 'https://github.com/davidwtbuxton/django-mini',
    description = 'Run plug-able Django apps without a settings module',
    long_description = read('README.rst'),
    py_modules = ['djangomini'],
    scripts = ['django-mini.py'],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Utilities',
    ],
)
