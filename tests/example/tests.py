from django.core.urlresolvers import reverse
from django.test import TestCase


# Demonstrates that django-mini.py works for running tests.
class ExampleTestCase(TestCase):
    urls = 'example.urls'

    def test_list_flavours(self):
        # List the available flavours for the example app.
        from example.models import Flavour

        for name in ('vanilla', 'chocolate', 'strawberry'):
            Flavour.objects.create(name=name)

        response = self.client.get(reverse('flavour_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('object_list', response.context)
        self.assertEqual(response.context['object_list'].count(), 3)
