from rest_framework import serializers
from routes.models import Route, Stop


class LocationSerializer(serializers.Serializer):
    address = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class StopSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    stop_type_display = serializers.CharField(source='get_stop_type_display', read_only=True)

    class Meta:
        model = Stop
        fields = [
            'id',
            'sequence',
            'stop_type',
            'stop_type_display',
            'location',
            'arrival_time',
            'departure_time',
            'duration_minutes',
            'description',
            'miles_from_previous',
            'cumulative_miles'
        ]

    def get_location(self, obj):
        return {
            'address': obj.address,
            'latitude': obj.latitude,
            'longitude': obj.longitude
        }


class RouteSerializer(serializers.ModelSerializer):
    stops = StopSerializer(many=True, read_only=True)

    class Meta:
        model = Route
        fields = [
            'id',
            'total_distance_miles',
            'total_duration_hours',
            'total_driving_hours',
            'total_on_duty_hours',
            'total_off_duty_hours',
            'compliance_status',
            'compliance_notes',
            'mapbox_route_geometry',
            'stops',
            'created_at'
        ]


class RouteDetailSerializer(serializers.ModelSerializer):
    stops = StopSerializer(many=True, read_only=True)
    trip_name = serializers.CharField(source='trip.trip_name', read_only=True)
    pickup_location_address = serializers.CharField(source='trip.pickup_location_address', read_only=True)
    dropoff_location_address = serializers.CharField(source='trip.dropoff_location_address', read_only=True)

    class Meta:
        model = Route
        fields = [
            'id',
            'trip_name',
            'pickup_location_address',
            'dropoff_location_address',
            'total_distance_miles',
            'total_duration_hours',
            'total_driving_hours',
            'total_on_duty_hours',
            'total_off_duty_hours',
            'compliance_status',
            'compliance_notes',
            'mapbox_route_geometry',
            'stops',
            'created_at'
        ]