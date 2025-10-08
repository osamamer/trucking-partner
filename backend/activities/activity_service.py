from .models import Activity
from django.utils import timezone

def start_activity(driver, activity_type):
    return Activity.objects.create(driver=driver, type=activity_type, start_time=timezone.now(), date=timezone.now().date(), active=True)

def end_activity(activity_id):
    activity = Activity.objects.get(id=activity_id)
    activity.end_time = timezone.now()
    activity.active = False
    activity.save()
    return activity
