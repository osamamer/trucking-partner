from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from trips.views import TripViewSet
from routes.views import RouteViewSet, StopViewSet
from logs.views import DailyLogViewSet, LogEntryViewSet

router = DefaultRouter()
router.register(r'trips', TripViewSet, basename='trip')
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'stops', StopViewSet, basename='stop')
router.register(r'daily-logs', DailyLogViewSet, basename='dailylog')
router.register(r'log-entries', LogEntryViewSet, basename='logentry')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]