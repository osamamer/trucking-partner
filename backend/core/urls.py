from django.urls import path, include
from rest_framework.routers import DefaultRouter

from trips.views import TripViewSet
from routes.views import RouteViewSet, StopViewSet
from logs.views import DailyLogViewSet, DutyStatusChangeViewSet

# Create router
router = DefaultRouter()

# Register viewsets
router.register(r'trips', TripViewSet, basename='trip')
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'stops', StopViewSet, basename='stop')
router.register(r'daily-logs', DailyLogViewSet, basename='dailylog')
router.register(r'duty-status-changes', DutyStatusChangeViewSet, basename='dutystatuschange')

# URL patterns
urlpatterns = [
    path('api/', include(router.urls)),
]