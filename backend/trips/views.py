from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Trip
from .serializers import (
    TripCreateSerializer,
    TripDetailSerializer,
    TripListSerializer,
    TripWithRouteSerializer
)
from routes.services import RouteGenerationService


class TripViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing trips

    Endpoints:
    - GET /api/trips/ - List all trips for current user
    - POST /api/trips/ - Create new trip
    - GET /api/trips/{id}/ - Get trip detail
    - PUT/PATCH /api/trips/{id}/ - Update trip
    - DELETE /api/trips/{id}/ - Delete trip
    - POST /api/trips/{id}/generate_route/ - Generate route for trip
    - GET /api/trips/{id}/with_route/ - Get trip with full route data
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return trips for current user only"""
        return Trip.objects.filter(user=self.request.user).select_related('route')

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return TripCreateSerializer
        elif self.action == 'list':
            return TripListSerializer
        elif self.action == 'with_route':
            return TripWithRouteSerializer
        return TripDetailSerializer

    def perform_create(self, serializer):
        """Set user when creating trip"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def generate_route(self, request, pk=None):
        """
        Generate route for a trip using RouteGenerationService

        POST /api/trips/{id}/generate_route/

        Optional body parameters:
        - mapbox_api_key: Override default API key
        """
        trip = self.get_object()

        # Check if route already exists
        if hasattr(trip, 'route'):
            return Response(
                {'error': 'Route already exists for this trip. Delete it first to regenerate.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get MapBox API key from request or settings
            mapbox_api_key = request.data.get('mapbox_api_key')
            if not mapbox_api_key:
                from django.conf import settings
                mapbox_api_key = getattr(settings, 'MAPBOX_API_KEY', None)

            if not mapbox_api_key:
                return Response(
                    {'error': 'MapBox API key not configured'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate route using service
            service = RouteGenerationService(mapbox_api_key)
            route = service.generate_and_save_route(trip)

            # Return trip with route
            serializer = TripWithRouteSerializer(trip)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Failed to generate route: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def with_route(self, request, pk=None):
        """
        Get trip with full route data

        GET /api/trips/{id}/with_route/
        """
        trip = self.get_object()
        serializer = TripWithRouteSerializer(trip)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_in_progress(self, request, pk=None):
        """
        Mark trip as in progress

        POST /api/trips/{id}/mark_in_progress/
        """
        trip = self.get_object()
        trip.status = 'in_progress'
        trip.save()
        serializer = self.get_serializer(trip)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """
        Mark trip as completed

        POST /api/trips/{id}/mark_completed/
        """
        trip = self.get_object()
        trip.status = 'completed'
        trip.save()
        serializer = self.get_serializer(trip)
        return Response(serializer.data)