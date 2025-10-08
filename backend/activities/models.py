from django.contrib.auth.models import User
from django.db import models

class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('OFF_DUTY', 'Off Duty'),
        ('SLEEPER_BERTH', 'Sleeper Berth'),
        ('DRIVING', 'Driving'),
        ('ON_DUTY', 'On Duty (Not Driving)'),
    ]
    type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    date = models.DateField()

    def __str__(self):
        return (f"Driver Name: {self.driver.username}\n"
                f"Activity Type: {self.type}"
                f"Start Time: {self.start_time}\n"
                f"End Time: {self.end_time}\n")

