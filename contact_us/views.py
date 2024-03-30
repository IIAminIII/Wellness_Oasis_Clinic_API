from django.shortcuts import render
from .models import ContactUs
from .serializers import ContactUsSerializer
from rest_framework import viewsets 
# Create your views here.

class ContactUsViewSet(viewsets.ModelViewSet):
    queryset = ContactUs.objects.all()
    serializer_class = ContactUsSerializer