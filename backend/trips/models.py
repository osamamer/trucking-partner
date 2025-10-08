from django.db import models

class Trip(models.Model):
    name = models.CharField(max_length=100)
    start_location = models.CharField(max_length=100)
    end_location = models.CharField(max_length=100)

    def __str__(self):
        return f"Name: {self.name}\n Start Location: {self.start_location}\n Destination: {self.end_location}"
