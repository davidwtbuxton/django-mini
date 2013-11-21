django-mini
===========

Django-mini is an MIT-licensed command-line utility for running `Django`_ management commands without a settings module. It is intended to help developers run and test stand-alone Django apps.

.. _Django: https://www.djangoproject.com/


Installation
------------

Install using pip from PyPI::

    pip install django-mini

Alternatively, `download the source`_, unpack it and install it like a typical Python distribution::

    python setup.py install

The installation consists of a single pure-Python module called ``djangomini`` and an executable script ``django-mini.py``. Django-mini assumes a recent version of Django is already installed.


Basic Usage
-----------

Django-mini has a few flags for configuring Django settings, and then any other arguments are passed to Django's management utility so it can do its stuff.

- ``--database <database>`` - to specify the default database.
- ``--app <appname>`` - adds your app package to Django's ``INSTALLED_APPS``.
- ``--admin`` - adds Django's built-in admin and its requirements.
- ``--debug-toolbar`` - adds Rob Hudson's `django-debug-toolbar`_ and its requirements.
- ``-p`` or ``--persisting`` - use an sqlite database named ``djangomini.sqlite``.
- ``--settings <module>`` - use an existing Django settings module as a base.
.. _django-debug-toolbar: https://github.com/django-debug-toolbar/django-debug-toolbar

If you don't use the persisting option or specify a database, django-mini will use an in-memory sqlite database (implying it will get destroyed after the command finishes).

To run Django with your app and the built-in admin, use a named database::

    django-mini.py --database /tmp/django.sqlite --admin --app myapp syncdb
    django-mini.py --database /tmp/django.sqlite --admin --app myapp runserver

Or use the persisting option::

    django-mini.py -p --admin syncdb
    django-mini.py -p --admin runserver

That will start Django's development server with the admin. The admin application will be available at ``http://localhost:8000/admin/`` and all other requests will be directed to your app, i.e. your app's ``myapp.urls`` is configured to serve all other requests.

To collect static files for an existing Django project but override the output directory::

    django-mini.py --settings myproject.settings --static-root /tmp/myproject-static collectstatic

`The full documentation`_ has more examples of use, including how to use other databases, how to change any setting, and how to mount an app at a particular URL.

.. _The full documentation: https://github.com/davidwtbuxton/django-mini/blob/master/docs/index.rst
.. _Download the source: https://github.com/davidwtbuxton/django-mini
