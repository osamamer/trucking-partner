from .views import LogViewSet
from django.urls import path


urlpatterns = [
    path('logs/list/', LogViewSet.as_view({'post': 'list'}), name='activity-start'),
    path('logs/<int:pk>/retrieve/', LogViewSet.as_view({'post': 'retrieve'}), name='activity-end'),
]