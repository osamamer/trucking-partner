from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Route, Stop, RouteSegment
from .serializers import (
    RouteDetailSerializer,
    RouteListSerializer,
    RouteWithLogsSerializer,
    StopSerializer,
    RouteSegmentSerializer
)


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing routes (read-only, routes are generated via Trip)

    Endpoints:
    - GET /api/routes/ - List all routes for current user's trips
    - GET /api/routes/{id}/ - Get route detail
    - GET /api/routes/{id}/with_logs/ - Get route with daily logs
    - GET /api/routes/{id}/stops/ - Get all stops for route
    - GET /api/routes/{id}/segments/ - Get all segments for route
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return routes for current user's trips"""
        return Route.objects.filter(
            trip__user=self.request.user
        ).select_related('trip').prefetch_related('stops', 'segments')

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return RouteListSerializer
        elif self.action == 'with_logs':
            return RouteWithLogsSerializer
        return RouteDetailSerializer

    @action(detail=True, methods=['get'])
    def with_logs(self, request, pk=None):
        """
        Get route with all daily logs

        GET /api/routes/{id}/with_logs/
        """
        route = self.get_object()
        serializer = RouteWithLogsSerializer(route)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stops(self, request, pk=None):
        """
        Get all stops for a route

        GET /api/routes/{id}/stops/
        """
        route = self.get_object()
        stops = route.stops.all()
        serializer = StopSerializer(stops, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def segments(self, request, pk=None):
        """
        Get all segments for a route

        GET /api/routes/{id}/segments/
        """
        route = self.get_object()
        segments = route.segments.all()
        serializer = RouteSegmentSerializer(segments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Get route summary statistics

        GET /api/routes/{id}/summary/
        """
        route = self.get_object()

        summary = {
            'total_distance_miles': route.total_distance_miles,
            'total_duration_hours': route.total_duration_hours,
            'total_driving_hours': route.total_driving_hours,
            'total_on_duty_hours': route.total_on_duty_hours,
            'compliance_status': route.compliance_status,
            'stops_breakdown': {
                'pickup': route.stops.filter(stop_type='pickup').count(),
                'dropoff': route.stops.filter(stop_type='dropoff').count(),
                'fuel': route.stops.filter(stop_type='fuel').count(),
                '30min_break': route.stops.filter(stop_type='30min_break').count(),
                '10hr_break': route.stops.filter(stop_type='10hr_break').count(),
            },
            'num_segments': route.segments.count(),
            'num_daily_logs': route.daily_logs.count(),
        }

        return Response(summary)


class StopViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing individual stops

    Endpoints:
    - GET /api/stops/ - List all stops for user's routes
    - GET /api/stops/{id}/ - Get stop detail
    """
    permission_classes = [IsAuthenticated]
    serializer_class = StopSerializer

    def get_queryset(self):
        """Return stops for current user's routes"""
        return Stop.objects.filter(
            route__trip__user=self.request.user
        ).select_related('route')