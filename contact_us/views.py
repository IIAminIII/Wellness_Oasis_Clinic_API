from django.shortcuts import render
from .models import ContactUs
from .serializers import ContactUsSerializer
from rest_framework import viewsets 
from Wellness_Oasis_Clinic.permissions import CreateOrAdminOnly
# Create your views here.

class ContactUsViewSet(viewsets.ModelViewSet):
    queryset = ContactUs.objects.all()
    serializer_class = ContactUsSerializer
    permission_classes = [CreateOrAdminOnly]
    http_method_names = ["get", "post", "patch", "head", "options"]
