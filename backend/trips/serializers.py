from rest_framework import serializers
from .models import Trip
from routes.models import Route, Stop
from logs.models import DailyLog, LogEntry

from logs.serializers import DailyLogListSerializer
from routes.serializers import RouteSerializer


class TripListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Trip
        fields = [
            'id',
            'trip_name',
            'status',
            'created_at',
            'current_location_address',
            'pickup_location_address',
            'dropoff_location_address',
            'current_cycle_hours_used',
            'total_distance_miles',
            'estimated_duration_hours',
            'days_required',
            'is_feasible',
            'feasibility_message'
        ]
        read_only_fields = [
            'id',
            'created_at',
            'total_distance_miles',
            'estimated_duration_hours',
            'days_required',
            'is_feasible',
            'feasibility_message'
        ]


class TripCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Trip
        fields = [
            'trip_name',
            'current_location_address',
            'pickup_location_address',
            'dropoff_location_address',
            'current_cycle_hours_used',
            'planned_start_time'
        ]

    def validate_current_cycle_hours_used(self, value):
        if value < 0 or value > 70:
            raise serializers.ValidationError("Cycle hours must be between 0 and 70")
        return value

class TripDetailSerializer(serializers.ModelSerializer):
    """Complete trip details with route and logs"""
    route = RouteSerializer(read_only=True)
    daily_logs = DailyLogListSerializer(many=True, read_only=True)

    class Meta:
        model = Trip
        fields = [
            'id',
            'trip_name',
            'status',
            'created_at',
            'updated_at',
            'current_location_address',
            'pickup_location_address',
            'dropoff_location_address',
            'current_cycle_hours_used',
            'planned_start_time',
            'total_distance_miles',
            'estimated_duration_hours',
            'days_required',
            'is_feasible',
            'feasibility_message',
            'route',
            'daily_logs'
        ]
