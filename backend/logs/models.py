from django.contrib.auth.models import User
from django.db import models
from trips.models import Trip
class Log(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='logs')

    date = models.DateField()

    driver = models.ForeignKey(User, related_name='driver_logs', on_delete=models.CASCADE)

    codriver = models.ForeignKey(User, related_name='codriver_logs', on_delete=models.CASCADE, null=True, blank=True)

    tractor_number = models.CharField(max_length=20)

    trailer_number = models.CharField(max_length=20, null=True, blank=True)

    shipper = models.CharField(max_length=100)
    shipper2 = models.CharField(max_length=100, default='N/A')

    commodity = models.CharField(max_length=100)
    commodity2 = models.CharField(max_length=100, default='N/A')

    load_number = models.CharField(max_length=100)
    load_number2 = models.CharField(max_length=100, default='N/A')


    driver_mileage = models.FloatField()

    truck_mileage = models.FloatField()

    onduty_time = models.FloatField()



