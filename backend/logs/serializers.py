from rest_framework import serializers
from .models import DailyLog, DutyStatusChange, LogAnnotation


class DutyStatusChangeSerializer(serializers.ModelSerializer):
    """
    Serializer for duty status changes (what gets drawn on the grid)
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_hours = serializers.SerializerMethodField()

    # Time formatted for display (HH:MM)
    start_time_display = serializers.SerializerMethodField()
    end_time_display = serializers.SerializerMethodField()

    class Meta:
        model = DutyStatusChange
        fields = [
            'id',
            'sequence',
            'status',
            'status_display',
            'start_time',
            'end_time',
            'start_time_display',
            'end_time_display',
            'duration_minutes',
            'duration_hours',
            'location',
            'location_lat',
            'location_lng',
            'remarks',
        ]

    def get_duration_hours(self, obj):
        return obj.duration_hours()

    def get_start_time_display(self, obj):
        return obj.start_time.strftime('%H:%M')

    def get_end_time_display(self, obj):
        return obj.end_time.strftime('%H:%M')


class LogAnnotationSerializer(serializers.ModelSerializer):
    """
    Serializer for log annotations/remarks
    """
    class Meta:
        model = LogAnnotation
        fields = [
            'id',
            'time',
            'annotation_type',
            'text',
            'created_at',
        ]


class DailyLogDetailSerializer(serializers.ModelSerializer):
    """
    Detailed daily log with all status changes
    """
    status_changes = DutyStatusChangeSerializer(many=True, read_only=True)
    annotations = LogAnnotationSerializer(many=True, read_only=True)
    log_date_display = serializers.SerializerMethodField()

    class Meta:
        model = DailyLog
        fields = [
            'id',
            'day_number',
            'log_date',
            'log_date_display',
            'driver_name',

            # Daily totals
            'total_off_duty_hours',
            'total_sleeper_berth_hours',
            'total_driving_hours',
            'total_on_duty_hours',

            # Locations
            'start_location',
            'end_location',

            # Odometer
            'start_odometer',
            'end_odometer',
            'total_miles',

            # Vehicle info
            'truck_number',
            'trailer_number',

            # Related data
            'status_changes',
            'annotations',

            'created_at',
        ]

    def get_log_date_display(self, obj):
        return obj.log_date.strftime('%B %d, %Y')


class DailyLogListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing daily logs
    """
    class Meta:
        model = DailyLog
        fields = [
            'id',
            'day_number',
            'log_date',
            'total_driving_hours',
            'total_on_duty_hours',
            'total_miles',
            'start_location',
            'end_location',
        ]


class DailyLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating daily logs programmatically
    Used by the log generation service
    """
    class Meta:
        model = DailyLog
        fields = [
            'route',
            'log_date',
            'day_number',
            'driver_name',
            'start_location',
            'end_location',
            'start_odometer',
            'end_odometer',
            'total_miles',
            'truck_number',
            'trailer_number',
        ]