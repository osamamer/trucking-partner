from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import DailyLog, DutyStatusChange
from .serializers import (
    DailyLogDetailSerializer,
    DailyLogListSerializer,
    DutyStatusChangeSerializer
)


class DailyLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing daily logs (read-only, logs are generated via Route)

    Endpoints:
    - GET /api/daily-logs/ - List all logs for current user
    - GET /api/daily-logs/{id}/ - Get log detail with status changes
    - GET /api/daily-logs/{id}/status_changes/ - Get status changes only
    - GET /api/daily-logs/{id}/export/ - Export log data for drawing
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return daily logs for current user's routes"""
        queryset = DailyLog.objects.filter(
            route__trip__user=self.request.user
        ).select_related('route', 'route__trip').prefetch_related('status_changes', 'annotations')

        # Filter by route if provided
        route_id = self.request.query_params.get('route_id', None)
        if route_id:
            queryset = queryset.filter(route_id=route_id)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return DailyLogListSerializer
        return DailyLogDetailSerializer

    @action(detail=True, methods=['get'])
    def status_changes(self, request, pk=None):
        """
        Get all status changes for a daily log

        GET /api/daily-logs/{id}/status_changes/
        """
        daily_log = self.get_object()
        status_changes = daily_log.status_changes.all()
        serializer = DutyStatusChangeSerializer(status_changes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """
        Export log data in format suitable for drawing ELD grid

        GET /api/daily-logs/{id}/export/

        Returns data structured for frontend to draw the log grid
        """
        daily_log = self.get_object()

        export_data = {
            'log_info': {
                'date': daily_log.log_date.isoformat(),
                'day_number': daily_log.day_number,
                'driver_name': daily_log.driver_name,
            },
            'totals': {
                'off_duty': float(daily_log.total_off_duty_hours),
                'sleeper_berth': float(daily_log.total_sleeper_berth_hours),
                'driving': float(daily_log.total_driving_hours),
                'on_duty': float(daily_log.total_on_duty_hours),
            },
            'locations': {
                'start': daily_log.start_location,
                'end': daily_log.end_location,
            },
            'odometer': {
                'start': daily_log.start_odometer,
                'end': daily_log.end_odometer,
                'total_miles': daily_log.total_miles,
            },
            'vehicle': {
                'truck_number': daily_log.truck_number,
                'trailer_number': daily_log.trailer_number,
            },
            'status_changes': [],
        }

        # Add status changes with time coordinates for grid drawing
        for change in daily_log.status_changes.all():
            # Calculate grid position (0-24 hours, 0-1440 minutes)
            start_hour = change.start_time.hour + change.start_time.minute / 60
            end_hour = change.end_time.hour + change.end_time.minute / 60

            # Map status to grid row (0-3)
            status_row_map = {
                'off_duty': 0,
                'sleeper_berth': 1,
                'driving': 2,
                'on_duty_not_driving': 3,
            }

            export_data['status_changes'].append({
                'sequence': change.sequence,
                'status': change.status,
                'status_display': change.get_status_display(),
                'start_time': change.start_time.isoformat(),
                'end_time': change.end_time.isoformat(),
                'start_hour': start_hour,
                'end_hour': end_hour,
                'duration_hours': change.duration_hours(),
                'grid_row': status_row_map.get(change.status, 0),
                'location': change.location,
                'remarks': change.remarks,
            })

        return Response(export_data)

    @action(detail=False, methods=['get'])
    def by_route(self, request):
        """
        Get all daily logs for a specific route

        GET /api/daily-logs/by_route/?route_id=123
        """
        route_id = request.query_params.get('route_id')
        if not route_id:
            return Response(
                {'error': 'route_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        daily_logs = self.get_queryset().filter(route_id=route_id)
        serializer = self.get_serializer(daily_logs, many=True)
        return Response(serializer.data)


class DutyStatusChangeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing individual duty status changes

    Endpoints:
    - GET /api/duty-status-changes/ - List all status changes
    - GET /api/duty-status-changes/{id}/ - Get status change detail
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DutyStatusChangeSerializer

    def get_queryset(self):
        """Return status changes for current user's logs"""
        return DutyStatusChange.objects.filter(
            daily_log__route__trip__user=self.request.user
        ).select_related('daily_log')