from rest_framework import generics
from .models import Service
from .serializers import ServiceSerializer


class ActiveServiceListAPIView(generics.ListAPIView):
    queryset = Service.objects.filter(is_active=True).order_by('title')
    serializer_class = ServiceSerializer

class ServiceDetailAPIView(generics.RetrieveAPIView):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    lookup_field = 'slug'
