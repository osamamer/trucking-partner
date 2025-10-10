from django.db import models
from trips.models import Trip


class DailyLog(models.Model):
    """
    ELD Daily Log - one per day of the trip
    Complies with FMCSA regulations
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='daily_logs')

    # Day Info
    day_number = models.IntegerField(help_text="Day 1, Day 2, etc.")
    log_date = models.DateField()

    # Hours Summary
    total_driving_hours = models.DecimalField(max_digits=4, decimal_places=2)
    total_on_duty_hours = models.DecimalField(max_digits=4, decimal_places=2)
    total_off_duty_hours = models.DecimalField(max_digits=4, decimal_places=2)
    total_sleeper_berth_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0
    )

    # Location Info
    start_location = models.CharField(max_length=500)
    end_location = models.CharField(max_length=500)
    total_miles = models.FloatField()

    # Compliance
    is_compliant = models.BooleanField(default=True)
    violations = models.JSONField(
        default=list,
        blank=True,
        help_text="List of any HOS violations"
    )

    # Grid Data for Visual Log
    log_grid_data = models.JSONField(
        null=True,
        blank=True,
        help_text="24-hour grid data for visual ELD log (15-minute intervals)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['trip', 'day_number']
        unique_together = ['trip', 'day_number']

    def __str__(self):
        return f"Day {self.day_number} - {self.trip.trip_name}"


class LogEntry(models.Model):
    """
    Individual duty status entry within a daily log
    Used to generate the 24-hour grid
    """
    DUTY_STATUS_CHOICES = [
        ('off_duty', 'Off Duty'),
        ('sleeper', 'Sleeper Berth'),
        ('driving', 'Driving'),
        ('on_duty', 'On Duty (Not Driving)'),
    ]

    daily_log = models.ForeignKey(
        DailyLog,
        on_delete=models.CASCADE,
        related_name='entries'
    )

    # Duty Status
    duty_status = models.CharField(max_length=20, choices=DUTY_STATUS_CHOICES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.IntegerField()

    # Location (if applicable)
    location = models.CharField(max_length=500, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Remarks
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['daily_log', 'start_time']

    def __str__(self):
        return f"{self.get_duty_status_display()} - {self.start_time.strftime('%H:%M')}"