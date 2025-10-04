from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView


class HomePageView(TemplateView):
    template_name = 'core/home.html'
