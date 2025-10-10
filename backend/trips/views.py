from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Trip
from .serializers import (
    TripListSerializer,
    TripCreateSerializer,
    TripDetailSerializer
)
from routes.services import generate_route_for_trip
import logging
logger = logging.getLogger(__name__)

class TripViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - GET /api/trips/ - List all trips
    - POST /api/trips/ - Create a new trip
    - GET /api/trips/{id}/ - Get trip details
    - PUT/PATCH /api/trips/{id}/ - Update trip
    - DELETE /api/trips/{id}/ - Delete trip
    - POST /api/trips/{id}/generate_route/ - Generate route for trip
    """
    queryset = Trip.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return TripCreateSerializer
        elif self.action == 'list':
            return TripListSerializer
        else:
            return TripDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()

        # Return the created trip with detail serializer
        response_serializer = TripDetailSerializer(trip)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def generate_route(self, request, pk=None):
        logger.info(f"=== GENERATE ROUTE CALLED for trip {pk} ===")
        trip = self.get_object()

        # Check if route already exists
        if hasattr(trip, 'route'):
            return Response(
                {'error': 'Route already exists for this trip. Delete it first to regenerate.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Generate the route
            logger.info(f"Trip found: {trip.trip_name}")
            logger.info(f"Starting route generation...")
            route = generate_route_for_trip(trip.id)

            # Return the updated trip with route
            serializer = TripDetailSerializer(trip)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate route: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )