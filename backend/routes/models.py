from django.db import models
from trips.models import Trip


class Route(models.Model):
    """
    Generated route for a trip with all calculated stops and compliance info
    """
    COMPLIANCE_CHOICES = [
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('warning', 'Warning'),
    ]

    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='route')

    # Route Overview
    total_distance_miles = models.FloatField()
    total_duration_hours = models.FloatField(help_text="Total elapsed time including breaks")
    total_driving_hours = models.FloatField(help_text="Actual driving time")
    total_on_duty_hours = models.FloatField(help_text="Driving + loading/unloading")
    total_off_duty_hours = models.FloatField(help_text="Rest breaks and sleeper berth")

    # Compliance
    compliance_status = models.CharField(
        max_length=20,
        choices=COMPLIANCE_CHOICES,
        default='compliant'
    )
    compliance_notes = models.TextField(blank=True)

    # MapBox Data
    mapbox_route_geometry = models.JSONField(
        null=True,
        blank=True,
        help_text="GeoJSON geometry from MapBox Directions API"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Route for {self.trip.trip_name}"


class Stop(models.Model):
    """
    Individual stop along the route (pickup, dropoff, rest, fuel, break)
    """
    STOP_TYPE_CHOICES = [
        ('current', 'Current Location'),
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
        ('fuel', 'Fuel Stop'),
        ('30min_break', '30-Minute Break'),
        ('10hr_break', '10-Hour Rest'),
    ]

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')

    # Stop Details
    sequence = models.IntegerField(help_text="Order of stop in route (0-indexed)")
    stop_type = models.CharField(max_length=20, choices=STOP_TYPE_CHOICES)

    # Location
    address = models.CharField(max_length=500)
    latitude = models.FloatField()
    longitude = models.FloatField()
    place_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="MapBox place ID if available"
    )

    # Timing
    arrival_time = models.DateTimeField()
    departure_time = models.DateTimeField()
    duration_minutes = models.IntegerField(help_text="How long stopped here")

    # Additional Info
    description = models.TextField(blank=True)
    miles_from_previous = models.FloatField(
        default=0,
        help_text="Distance from previous stop"
    )
    cumulative_miles = models.FloatField(
        default=0,
        help_text="Total miles driven up to this stop"
    )

    class Meta:
        ordering = ['route', 'sequence']
        unique_together = ['route', 'sequence']

    def __str__(self):
        return f"{self.get_stop_type_display()} - {self.address}"
