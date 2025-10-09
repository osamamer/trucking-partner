from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Trip(models.Model):
    """
    Main trip model - stores user input and high-level trip information
    """
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # User who created the trip
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips')

    # Trip identification
    trip_name = models.CharField(max_length=200, help_text="Name/description of trip")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')

    # Input locations (as text addresses or coordinates)
    current_location_address = models.CharField(max_length=500)
    current_location_lat = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    current_location_lng = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])

    pickup_location_address = models.CharField(max_length=500)
    pickup_location_lat = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    pickup_location_lng = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])

    dropoff_location_address = models.CharField(max_length=500)
    dropoff_location_lat = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    dropoff_location_lng = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])

    # ELD cycle information
    current_cycle_hours_used = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(70)],
        help_text="Hours already used in current 8-day cycle"
    )

    # Trip timing
    planned_start_time = models.DateTimeField(help_text="When driver plans to start")

    # Trip summary (populated after route generation)
    total_distance_miles = models.FloatField(null=True, blank=True)
    total_duration_hours = models.FloatField(null=True, blank=True)
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    days_required = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.trip_name} ({self.status})"