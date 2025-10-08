from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import ActivitySerializer
from . import activity_service

class ActivityViewSet(viewsets.ViewSet):
    def start(self, request):
        activity = activity_service.start_activity(request.user, request.data['activity_type'])
        return Response(ActivitySerializer(activity).data)

    def end(self, request, pk=None):
        activity = activity_service.end_activity(pk)
        return Response(ActivitySerializer(activity).data)
