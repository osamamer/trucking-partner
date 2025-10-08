from django.shortcuts import render

from django.shortcuts import render
from rest_framework.response import Response
from .models import Log
from rest_framework import viewsets
from .serializers import LogSerializer


class LogViewSet(viewsets.ViewSet):
    def list(self, request):
        logs = Log.objects.all()
        serializer = LogSerializer(logs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        log = Log.objects.get(pk=pk)
        serializer = LogSerializer(log)
        return Response(serializer.data)