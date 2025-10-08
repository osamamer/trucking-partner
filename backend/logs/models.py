from django.db import models
from trips.models import Trip
class Log(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField()
    mileage = models.FloatField()


