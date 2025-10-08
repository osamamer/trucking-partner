from django.shortcuts import render
from .models import Trip
from rest_framework import viewsets
from .serializers import TripSerializer


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer