from rest_framework import serializers
from .models import Trip
from django.utils import timezone

from routes.serializers import RouteDetailSerializer


class TripCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new trip with user inputs
    """
    class Meta:
        model = Trip
        fields = [
            'trip_name',
            'current_location_address',
            'current_location_lat',
            'current_location_lng',
            'pickup_location_address',
            'pickup_location_lat',
            'pickup_location_lng',
            'dropoff_location_address',
            'dropoff_location_lat',
            'dropoff_location_lng',
            'current_cycle_hours_used',
            'planned_start_time',
        ]

    def validate_current_cycle_hours_used(self, value):
        """Ensure cycle hours are within valid range"""
        if value < 0 or value > 70:
            raise serializers.ValidationError("Cycle hours must be between 0 and 70")
        return value

    def validate_planned_start_time(self, value):
        """Ensure start time is not in the past"""
        if value < timezone.now():
            raise serializers.ValidationError("Start time cannot be in the past")
        return value

    def validate(self, data):
        """Cross-field validation"""
        # Ensure pickup and dropoff are different
        if (data['pickup_location_lat'] == data['dropoff_location_lat'] and
                data['pickup_location_lng'] == data['dropoff_location_lng']):
            raise serializers.ValidationError("Pickup and dropoff locations must be different")
        return data


class TripDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for viewing trip information
    Includes route and log relationships
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    has_route = serializers.SerializerMethodField()
    num_daily_logs = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'id',
            'user_email',
            'trip_name',
            'status',
            'created_at',
            'updated_at',

            # Locations
            'current_location_address',
            'current_location_lat',
            'current_location_lng',
            'pickup_location_address',
            'pickup_location_lat',
            'pickup_location_lng',
            'dropoff_location_address',
            'dropoff_location_lat',
            'dropoff_location_lng',

            # ELD info
            'current_cycle_hours_used',
            'planned_start_time',

            # Summary (populated after route generation)
            'total_distance_miles',
            'total_duration_hours',
            'estimated_arrival_time',
            'days_required',

            # Computed fields
            'has_route',
            'num_daily_logs',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'total_distance_miles',
            'total_duration_hours', 'estimated_arrival_time', 'days_required'
        ]

    def get_has_route(self, obj):
        """Check if route has been generated"""
        return hasattr(obj, 'route')

    def get_num_daily_logs(self, obj):
        """Count daily logs if route exists"""
        if hasattr(obj, 'route'):
            return obj.route.daily_logs.count()
        return 0


class TripListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing trips
    """
    class Meta:
        model = Trip
        fields = [
            'id',
            'trip_name',
            'status',
            'created_at',
            'pickup_location_address',
            'dropoff_location_address',
            'total_distance_miles',
            'days_required',
        ]

class TripWithRouteSerializer(serializers.ModelSerializer):
    """
    Trip with embedded route data - useful for "trip detail" view
    """
    route = RouteDetailSerializer(read_only=True)

    class Meta:
        model = Trip
        fields = [
            'id',
            'trip_name',
            'status',
            'created_at',

            # Locations
            'current_location_address',
            'current_location_lat',
            'current_location_lng',
            'pickup_location_address',
            'pickup_location_lat',
            'pickup_location_lng',
            'dropoff_location_address',
            'dropoff_location_lat',
            'dropoff_location_lng',

            # Trip summary
            'total_distance_miles',
            'total_duration_hours',
            'estimated_arrival_time',
            'days_required',

            # Embedded route
            'route',
        ]