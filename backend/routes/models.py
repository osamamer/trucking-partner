from django.db import models
from django.contrib.postgres.fields import JSONField  # Use this if PostgreSQL, otherwise see note below


class Route(models.Model):
    """
    Generated route for a trip - one route per trip
    """
    trip = models.OneToOneField('trips.Trip', on_delete=models.CASCADE, related_name='route')

    # Route metadata
    created_at = models.DateTimeField(auto_now_add=True)

    # MapBox route data
    mapbox_geometry = models.JSONField(help_text="GeoJSON geometry from MapBox for drawing route")

    # Summary statistics
    total_distance_miles = models.FloatField()
    total_duration_hours = models.FloatField()

    # ELD compliance summary
    total_driving_hours = models.FloatField()
    total_on_duty_hours = models.FloatField()
    cycle_hours_after_trip = models.FloatField(help_text="Cycle hours used after completing trip")
    compliance_status = models.CharField(max_length=20, default='compliant')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Route for {self.trip.trip_name}"


class Stop(models.Model):
    """
    Individual stop on the route (pickup, dropoff, fuel, breaks, etc.)
    """
    STOP_TYPE_CHOICES = [
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
        ('fuel', 'Fuel Stop'),
        ('30min_break', '30-Minute Break'),
        ('10hr_break', '10-Hour Rest'),
        ('rest_break', 'Rest Break'),
    ]

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')

    # Stop order in the route
    sequence = models.IntegerField(help_text="Order of this stop in the route")

    # Location
    location_address = models.CharField(max_length=500, blank=True)
    location_lat = models.FloatField()
    location_lng = models.FloatField()

    # Stop details
    stop_type = models.CharField(max_length=20, choices=STOP_TYPE_CHOICES)
    description = models.TextField(blank=True)

    # Timing
    arrival_time = models.DateTimeField()
    departure_time = models.DateTimeField()
    duration_minutes = models.IntegerField()

    class Meta:
        ordering = ['sequence']
        indexes = [
            models.Index(fields=['route', 'sequence']),
        ]

    def __str__(self):
        return f"{self.get_stop_type_display()} - Stop {self.sequence}"


class RouteSegment(models.Model):
    """
    Driving segment between two stops
    """
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='segments')

    # Segment order
    sequence = models.IntegerField(help_text="Order of this segment in the route")

    # Start and end stops
    start_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='segments_starting')
    end_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='segments_ending')

    # Segment details
    distance_miles = models.FloatField()
    duration_minutes = models.FloatField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        ordering = ['sequence']
        indexes = [
            models.Index(fields=['route', 'sequence']),
        ]

    def __str__(self):
        return f"Segment {self.sequence}: {self.distance_miles} miles"