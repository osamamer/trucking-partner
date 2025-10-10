from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Trip(models.Model):
    """
    Main trip entity - stores the initial request and overall trip metadata
    """
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # Basic Info
    trip_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Input Fields (from user)
    current_location_address = models.CharField(max_length=500)
    current_location_latitude = models.FloatField(null=True, blank=True)
    current_location_longitude = models.FloatField(null=True, blank=True)

    pickup_location_address = models.CharField(max_length=500)
    pickup_location_latitude = models.FloatField(null=True, blank=True)
    pickup_location_longitude = models.FloatField(null=True, blank=True)

    dropoff_location_address = models.CharField(max_length=500)
    dropoff_location_latitude = models.FloatField(null=True, blank=True)
    dropoff_location_longitude = models.FloatField(null=True, blank=True)

    current_cycle_hours_used = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(70)],
        help_text="Hours already used in current 8-day cycle (0-70)"
    )

    planned_start_time = models.DateTimeField(default=timezone.now)

    # Calculated Fields (after route generation)
    total_distance_miles = models.FloatField(null=True, blank=True)
    estimated_duration_hours = models.FloatField(null=True, blank=True)
    days_required = models.IntegerField(null=True, blank=True)
    is_feasible = models.BooleanField(
        default=True,
        help_text="Whether driver has enough hours to complete this trip"
    )
    feasibility_message = models.TextField(
        blank=True,
        help_text="Explanation if trip is not feasible"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.trip_name} ({self.status})"
