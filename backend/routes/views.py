from rest_framework import viewsets
from rest_framework.response import Response
from .models import Route, Stop
from .serializers import RouteDetailSerializer, StopSerializer


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    - GET /api/routes/ - List all routes
    - GET /api/routes/{id}/ - Get route details with stops
    """

    queryset = Route.objects.all().select_related('trip').prefetch_related('stops')
    serializer_class = RouteDetailSerializer


class StopViewSet(viewsets.ReadOnlyModelViewSet):
    """
    - GET /api/stops/ - List all stops
    - GET /api/stops/{id}/ - Get stop details
    """

    queryset = Stop.objects.all().select_related('route')
    serializer_class = StopSerializer