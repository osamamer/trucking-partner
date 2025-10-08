from .views import ActivityViewSet
from django.urls import path

urlpatterns = [
    path('activities/start/', ActivityViewSet.as_view({'post': 'start'}), name='activity-start'),
    path('activities/<int:pk>/end/', ActivityViewSet.as_view({'post': 'end'}), name='activity-end'),
    # path('activities/<int:pk>/pause/', ActivityViewSet.as_view({'post': 'pause'}), name='activity-pause'),
    # path('activities/<int:pk>/resume/', ActivityViewSet.as_view({'post': 'resume'}), name='activity-resume'),
]