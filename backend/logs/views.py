from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import JsonResponse

from .models import DailyLog, LogEntry
from .serializers import DailyLogSerializer, DailyLogListSerializer, LogEntrySerializer


class DailyLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    - GET /api/daily-logs/ - List all daily logs
    - GET /api/daily-logs/{id}/ - Get daily log details
    - GET /api/daily-logs/{id}/export/ - Export log as PDF/JSON
    - GET /api/daily-logs/?trip={trip_id} - Filter logs by trip
    """

    queryset = DailyLog.objects.all().select_related('trip').prefetch_related('entries')

    def get_serializer_class(self):
        if self.action == 'list':
            return DailyLogListSerializer
        return DailyLogSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by trip if provided
        trip_id = self.request.query_params.get('trip', None)
        if trip_id:
            queryset = queryset.filter(trip_id=trip_id)

        return queryset

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        daily_log = self.get_object()
        format_type = request.query_params.get('format', 'json')

        if format_type == 'json':
            serializer = DailyLogSerializer(daily_log)
            return Response(serializer.data)

        elif format_type == 'pdf':
            # TODO: Implement PDF generation with ELD grid
            return Response(
                {'message': 'PDF export coming soon'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )

        else:
            return Response(
                {'error': 'Invalid format. Use json or pdf'},
                status=status.HTTP_400_BAD_REQUEST
            )


class LogEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoints:
    - GET /api/log-entries/ - List all log entries
    - GET /api/log-entries/{id}/ - Get log entry details
    """

    queryset = LogEntry.objects.all().select_related('daily_log')
    serializer_class = LogEntrySerializer