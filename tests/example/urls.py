try:
    from django.conf.urls import patterns, include, url
except ImportError:
    # Django 1.3
    from django.conf.urls.defaults import patterns, include, url
from .views import FlavourListView


urlpatterns = patterns('',
    url(r'^flavours/$', FlavourListView.as_view(), name='flavour_list'),
)
