from django.shortcuts import render
from .models import Activity
from rest_framework import viewsets
from .serializers import ActivitySerializer


class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer