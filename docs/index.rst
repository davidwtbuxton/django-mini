.. django-mini documentation master file, created by
   sphinx-quickstart on Fri Jan 25 21:01:09 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Django-mini
===========

.. toctree::
   :maxdepth: 2

About
-----

Django-mini is a command-line utility for running `Django`_ management commands without a settings module. It is intended to help developers run and test stand-alone Django apps.

The code is distributed under the MIT license. The project's home page is https://github.com/davidwtbuxton/django-mini

Django-mini works with Django 1.3, 1.4 and 1.5 on Python 2.5, 2.6, 2.7 and 3.3.

.. _Django: https://www.djangoproject.com/


Installation
------------

Install using pip from PyPI::

    pip install django-mini

Alternatively, `download the source`_, unpack it and install it like a typical Python distribution::

    python setup.py install

The installation consists of a single pure-Python module called ``djangomini`` and an executable script ``django-mini.py``. Django-mini assumes a recent version of Django is already installed.

.. _Download the source: https://github.com/davidwtbuxton/django-mini

Adding an App
-------------

Use `-a` or `--app` followed by the name of an app. The app is added to ``INSTALLED_APPS`` and configured in the ``ROOT_URLCONF``. Can be used more than once.

Example::

    django-mini.py -a myapp -a otherapp -p runserver

This is equivalent to ``INSTALLED_APPS = ['myapp', 'otherapp']`` in Django's settings and

::

    urlpatterns = patterns('',
        url(r'^', include('myapp.urls')),
        url(r'^', include('otherapp.urls')),
    )

in the ``ROOT_URLCONF`` module.

To mount your app at a specific path add the path name after the app name, separated by a colon (useful when you have multiple apps)::

    django-mini.py -a myapp:foo -a otherapp:bar -p runserver

This is equivalent to

::

    urlpatterns = patterns('',
        url(r'^foo/', include('myapp.urls')),
        url(r'^bar/', include('otherapp.urls')),
    )


Adding Django's Admin App
-------------------------

Use ``--admin`` to add Django's admin app and its dependencies to the settings.

The path is hard-coded to ``/admin/``, and it always comes first in the ``ROOT_URLCONF`` patterns.


Adding django-debug-toolbar
---------------------------

Use ``--debug-toolbar`` to enable Rob Hudson's popular `django-debug-toolbar`_ Django add-on. This adds it to the settings, including the required middleware as well as setting ``DEBUG = True`` and ``INTERNAL_IPS = ('127.0.0.1',)``.

 
.. _django-debug-toolbar: https://github.com/django-debug-toolbar/django-debug-toolbar

Configuring a Database
----------------------

Use ``-d`` or ``--database`` followed by a database connection string to configure Django with a database. The database connection string uses the same format used by SQLAlchemy.

If you don't specify a database Django-mini uses ``sqlite:///:memory:``, i.e. an in-memory database that will get destroyed after the command is run.

If you use the ``-p`` or ``--persisting`` option Django-mini will use an on-disk sqlite database. It will be named ``djangomini.sqlite`` and will be created in the current working directory (i.e. as if you had specified ``--database sqlite:///djangomini.sqlite``).

The format of the database connection string is

::

    <engine>://<username>:<password>@<host>:<port>/<database>?<options>

This next example configures a MySQL database on localhost::

    mysql://root@localhost/mydatabase

It is equivalent to the following in your Django settings::

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'mydatabase',
            'HOST': 'localhost',
            'PORT': '',
            'USER': 'root',
            'PASSWORD': '',
            'OPTIONS': {},
        },
    }

Django-mini knows about the built-in database backends so you can use ``postgresql``, ``mysql``, ``sqlite`` or ``oracle`` for the engine name. For a custom back-end you must specify the package name, e.g ``--database myapp.backends.customdb://localhost/mydatabase``.


Configuring Any Django Setting
-------------------------------

Any long option that comes before the Django command, other than the options described above, is assumed to be a setting name followed by a value. The option name is converted to upper case with dashes replaced by underscores, and the value is evaluated as a Python expression, falling back to a string if it isn't a valid expression.

For example to set ``DEBUG = False`` use ``--debug False``. Or to set ``TIME_ZONE = 'Europe/London'`` use ``--time-zone Europe/London``.

You can use more complicated values such as lists but will have to keep in mind your shell's rules for escaping special characters.


Passing Options to the Django Command
-------------------------------------

Any options or arguments that come after the first positional argument are passed as-is to the Django commmand.

For example to run syncdb with the admin but without prompting for input::

    django-mini.py --admin -p syncdb --noinput

