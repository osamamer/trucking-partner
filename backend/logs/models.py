from django.db import models
from decimal import Decimal


class DailyLog(models.Model):
    """
    Represents one daily log sheet (24-hour period)
    """
    route = models.ForeignKey('routes.Route', on_delete=models.CASCADE, related_name='daily_logs')

    # Log identification
    log_date = models.DateField(help_text="Date this log covers")
    day_number = models.IntegerField(help_text="Day number in the trip (1, 2, 3, etc.)")

    # Driver info (could be expanded later)
    driver_name = models.CharField(max_length=200, blank=True)

    # Daily totals (in hours)
    total_off_duty_hours = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'))
    total_sleeper_berth_hours = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'))
    total_driving_hours = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'))
    total_on_duty_hours = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'))

    # Beginning and ending locations
    start_location = models.CharField(max_length=500, blank=True)
    end_location = models.CharField(max_length=500, blank=True)

    # Odometer readings
    start_odometer = models.IntegerField(null=True, blank=True)
    end_odometer = models.IntegerField(null=True, blank=True)
    total_miles = models.IntegerField(null=True, blank=True)

    # Trailer/truck numbers (optional)
    truck_number = models.CharField(max_length=50, blank=True)
    trailer_number = models.CharField(max_length=50, blank=True)

    # Created timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['day_number']
        unique_together = ['route', 'day_number']
        indexes = [
            models.Index(fields=['route', 'day_number']),
        ]

    def __str__(self):
        return f"Day {self.day_number} - {self.log_date}"


class DutyStatusChange(models.Model):
    """
    Represents a change in duty status on the ELD log
    This is what gets drawn on the time grid
    """
    DUTY_STATUS_CHOICES = [
        ('off_duty', 'Off Duty'),
        ('sleeper_berth', 'Sleeper Berth'),
        ('driving', 'Driving'),
        ('on_duty_not_driving', 'On Duty (Not Driving)'),
    ]

    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name='status_changes')

    # Duty status
    status = models.CharField(max_length=30, choices=DUTY_STATUS_CHOICES)

    # Timing
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.IntegerField()

    # Location where status change occurred
    location = models.CharField(max_length=500, blank=True)
    location_lat = models.FloatField(null=True, blank=True)
    location_lng = models.FloatField(null=True, blank=True)

    # Remarks/notes
    remarks = models.TextField(blank=True)

    # Sequence in the day
    sequence = models.IntegerField(help_text="Order of status change in the day")

    class Meta:
        ordering = ['sequence']
        indexes = [
            models.Index(fields=['daily_log', 'sequence']),
        ]

    def __str__(self):
        return f"{self.get_status_display()}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    def duration_hours(self):
        """Return duration in hours as decimal"""
        return round(self.duration_minutes / 60, 2)


class LogAnnotation(models.Model):
    """
    Annotations/remarks on the log (for special events, inspections, etc.)
    """
    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name='annotations')

    time = models.DateTimeField()
    annotation_type = models.CharField(max_length=50, blank=True)
    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['time']

    def __str__(self):
        return f"Annotation at {self.time.strftime('%H:%M')}"
