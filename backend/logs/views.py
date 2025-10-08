from django.shortcuts import render

from django.shortcuts import render
from .models import Log
from rest_framework import viewsets
from .serializers import LogSerializer


class LogViewSet(viewsets.ModelViewSet):
    queryset = Log.objects.all()
    serializer_class = LogSerializer