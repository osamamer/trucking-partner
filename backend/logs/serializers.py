from rest_framework import serializers
from logs.models import DailyLog, LogEntry


class LogEntrySerializer(serializers.ModelSerializer):
    duty_status_display = serializers.CharField(source='get_duty_status_display', read_only=True)

    class Meta:
        model = LogEntry
        fields = [
            'id',
            'duty_status',
            'duty_status_display',
            'start_time',
            'end_time',
            'duration_minutes',
            'location',
            'latitude',
            'longitude',
            'remarks'
        ]


class DailyLogSerializer(serializers.ModelSerializer):
    entries = LogEntrySerializer(many=True, read_only=True)
    class Meta:
        model = DailyLog
        fields = [
            'id',
            'day_number',
            'log_date',
            'total_driving_hours',
            'total_on_duty_hours',
            'total_off_duty_hours',
            'total_sleeper_berth_hours',
            'start_location',
            'end_location',
            'total_miles',
            'is_compliant',
            'violations',
            'log_grid_data',
            'entries'
        ]


class DailyLogListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLog
        fields = [
            'id',
            'day_number',
            'log_date',
            'total_driving_hours',
            'total_on_duty_hours',
            'total_off_duty_hours',
            'start_location',
            'end_location',
            'total_miles',
            'is_compliant'
        ]
