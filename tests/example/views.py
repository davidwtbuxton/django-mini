from django.views.generic import ListView
from .models import Flavour


class FlavourListView(ListView):
    model = Flavour
