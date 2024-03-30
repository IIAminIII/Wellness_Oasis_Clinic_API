from django.shortcuts import render
from .models import Service
from .serializers import ServiceSerializer
from rest_framework import viewsets
# Create your views here.


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer