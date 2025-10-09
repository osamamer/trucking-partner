from rest_framework import serializers
from .models import Route, Stop, RouteSegment
from logs.serializers import DailyLogDetailSerializer


class StopSerializer(serializers.ModelSerializer):
    """
    Serializer for individual stops
    """
    stop_type_display = serializers.CharField(source='get_stop_type_display', read_only=True)

    class Meta:
        model = Stop
        fields = [
            'id',
            'sequence',
            'location_address',
            'location_lat',
            'location_lng',
            'stop_type',
            'stop_type_display',
            'description',
            'arrival_time',
            'departure_time',
            'duration_minutes',
        ]


class RouteSegmentSerializer(serializers.ModelSerializer):
    """
    Serializer for route segments
    """
    class Meta:
        model = RouteSegment
        fields = [
            'id',
            'sequence',
            'distance_miles',
            'duration_minutes',
            'start_time',
            'end_time',
        ]


class RouteDetailSerializer(serializers.ModelSerializer):
    """
    Detailed route serializer with all stops and segments
    """
    trip_name = serializers.CharField(source='trip.trip_name', read_only=True)
    stops = StopSerializer(many=True, read_only=True)
    segments = RouteSegmentSerializer(many=True, read_only=True)

    # ELD summary fields
    num_fuel_stops = serializers.SerializerMethodField()
    num_30min_breaks = serializers.SerializerMethodField()
    num_10hr_breaks = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = [
            'id',
            'trip_name',
            'created_at',

            # Route data
            'mapbox_geometry',
            'total_distance_miles',
            'total_duration_hours',

            # ELD compliance
            'total_driving_hours',
            'total_on_duty_hours',
            'cycle_hours_after_trip',
            'compliance_status',

            # Stops and segments
            'stops',
            'segments',

            # Summary
            'num_fuel_stops',
            'num_30min_breaks',
            'num_10hr_breaks',
        ]

    def get_num_fuel_stops(self, obj):
        return obj.stops.filter(stop_type='fuel').count()

    def get_num_30min_breaks(self, obj):
        return obj.stops.filter(stop_type='30min_break').count()

    def get_num_10hr_breaks(self, obj):
        return obj.stops.filter(stop_type='10hr_break').count()


class RouteListSerializer(serializers.ModelSerializer):
    """
    Lightweight route serializer for listing
    """
    trip_name = serializers.CharField(source='trip.trip_name', read_only=True)
    num_stops = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = [
            'id',
            'trip_name',
            'created_at',
            'total_distance_miles',
            'total_duration_hours',
            'compliance_status',
            'num_stops',
        ]

    def get_num_stops(self, obj):
        return obj.stops.count()





class RouteWithLogsSerializer(serializers.ModelSerializer):
    """
    Route with embedded daily logs - useful for "route with logs" view
    """
    daily_logs = DailyLogDetailSerializer(many=True, read_only=True)
    trip_name = serializers.CharField(source='trip.trip_name', read_only=True)

    class Meta:
        model = Route
        fields = [
            'id',
            'trip_name',
            'total_distance_miles',
            'total_duration_hours',
            'total_driving_hours',
            'total_on_duty_hours',
            'compliance_status',
            'daily_logs',
        ]