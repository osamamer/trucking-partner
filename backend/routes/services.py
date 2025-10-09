from datetime import datetime, timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from trips.models import Trip
from .models import Route, Stop, RouteSegment
from logs.models import DailyLog, DutyStatusChange

# Import the core routing logic
import sys
import os
# Add the path where route_service.py is located
# Adjust this path based on where you put route_service.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from route_service import RouteService, Location, ELDRules


class RouteGenerationService:
    """
    Service that generates routes and saves them to Django models
    """

    def __init__(self, mapbox_api_key: str):
        """
        Initialize service with MapBox API key

        Args:
            mapbox_api_key: MapBox API key for routing
        """
        self.mapbox_api_key = mapbox_api_key
        self.route_service = RouteService(mapbox_api_key)

    @transaction.atomic
    def generate_and_save_route(self, trip: Trip) -> Route:
        """
        Generate a complete route and save all related data to database

        This is the main entry point that:
        1. Generates route using RouteService
        2. Saves Route, Stops, and Segments to database
        3. Generates and saves Daily Logs
        4. Updates Trip with summary data

        Args:
            trip: Trip object to generate route for

        Returns:
            Route object with all related data saved
        """

        # Step 1: Convert Trip locations to Location objects
        current_location = Location(
            latitude=trip.current_location_lat,
            longitude=trip.current_location_lng,
            address=trip.current_location_address
        )

        pickup_location = Location(
            latitude=trip.pickup_location_lat,
            longitude=trip.pickup_location_lng,
            address=trip.pickup_location_address
        )

        dropoff_location = Location(
            latitude=trip.dropoff_location_lat,
            longitude=trip.dropoff_location_lng,
            address=trip.dropoff_location_address
        )

        # Step 2: Generate route using RouteService
        route_data = self.route_service.generate_route(
            current_location=current_location,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            current_cycle_hours_used=trip.current_cycle_hours_used,
            start_time=trip.planned_start_time
        )

        # Step 3: Create Route object
        route = Route.objects.create(
            trip=trip,
            mapbox_geometry=route_data['mapbox_geometry'],
            total_distance_miles=route_data['total_distance_miles'],
            total_duration_hours=route_data['total_duration_hours'],
            total_driving_hours=route_data['eld_summary']['total_driving_hours'],
            total_on_duty_hours=route_data['eld_summary']['total_on_duty_hours'],
            cycle_hours_after_trip=route_data['eld_summary']['cycle_hours_used'],
            compliance_status=route_data['eld_summary']['compliance_status']
        )

        # Step 4: Save all stops
        stop_objects = self._save_stops(route, route_data['stops'])

        # Step 5: Save all segments
        self._save_segments(route, route_data['segments'], stop_objects)

        # Step 6: Generate and save daily logs
        self._generate_daily_logs(route, route_data, stop_objects)

        # Step 7: Update trip with summary data
        trip.total_distance_miles = route_data['total_distance_miles']
        trip.total_duration_hours = route_data['total_duration_hours']
        trip.estimated_arrival_time = route_data['estimated_arrival']
        trip.days_required = route_data['days_required']
        trip.save()

        return route

    def _save_stops(self, route: Route, stops_data: list) -> dict:
        """
        Save all stops to database

        Args:
            route: Route object
            stops_data: List of stop dictionaries from route_service

        Returns:
            Dictionary mapping sequence to Stop objects
        """
        stop_objects = {}

        for idx, stop_data in enumerate(stops_data):
            location = stop_data['location']

            stop = Stop.objects.create(
                route=route,
                sequence=idx,
                location_address=location['address'],
                location_lat=location['latitude'],
                location_lng=location['longitude'],
                stop_type=stop_data['stop_type'],
                description=stop_data['description'],
                arrival_time=datetime.fromisoformat(stop_data['arrival_time']),
                departure_time=datetime.fromisoformat(stop_data['departure_time']),
                duration_minutes=stop_data['duration_minutes']
            )

            stop_objects[idx] = stop

        return stop_objects

    def _save_segments(self, route: Route, segments_data: list, stop_objects: dict):
        """
        Save all route segments to database

        Args:
            route: Route object
            segments_data: List of segment dictionaries from route_service
            stop_objects: Dictionary of Stop objects by sequence
        """
        for idx, segment_data in enumerate(segments_data):
            # Map segments to stops (segment 0 is between stop 0 and stop 1)
            start_stop = stop_objects[idx]
            end_stop = stop_objects[idx + 1]

            RouteSegment.objects.create(
                route=route,
                sequence=idx,
                start_stop=start_stop,
                end_stop=end_stop,
                distance_miles=segment_data['distance_miles'],
                duration_minutes=segment_data['duration_minutes'],
                start_time=datetime.fromisoformat(segment_data['start_time']),
                end_time=datetime.fromisoformat(segment_data['end_time'])
            )

    def _generate_daily_logs(self, route: Route, route_data: dict, stop_objects: dict):
        """
        Generate daily ELD logs based on route and stops

        This breaks down the trip into 24-hour periods and creates
        DailyLog and DutyStatusChange entries

        Args:
            route: Route object
            route_data: Complete route data from route_service
            stop_objects: Dictionary of Stop objects
        """
        # Get trip start and end times
        stops_data = route_data['stops']
        start_time = datetime.fromisoformat(stops_data[0]['arrival_time'])
        end_time = datetime.fromisoformat(stops_data[-1]['departure_time'])

        # Calculate number of days
        total_days = (end_time.date() - start_time.date()).days + 1

        # Generate a log for each day
        for day_num in range(total_days):
            log_date = (start_time + timedelta(days=day_num)).date()

            # Define the 24-hour period for this log
            day_start = datetime.combine(log_date, datetime.min.time())
            day_end = day_start + timedelta(days=1)

            # Make timezone-aware if needed
            if timezone.is_aware(start_time):
                day_start = timezone.make_aware(day_start)
                day_end = timezone.make_aware(day_end)

            # Create daily log
            daily_log = self._create_daily_log_for_day(
                route=route,
                log_date=log_date,
                day_number=day_num + 1,
                day_start=day_start,
                day_end=day_end,
                stops_data=stops_data,
                stop_objects=stop_objects
            )

    def _create_daily_log_for_day(
            self,
            route: Route,
            log_date,
            day_number: int,
            day_start: datetime,
            day_end: datetime,
            stops_data: list,
            stop_objects: dict
    ) -> DailyLog:
        """
        Create a daily log for a specific 24-hour period

        Args:
            route: Route object
            log_date: Date of the log
            day_number: Day number (1, 2, 3...)
            day_start: Start of 24-hour period
            day_end: End of 24-hour period
            stops_data: All stops data
            stop_objects: Stop objects dictionary

        Returns:
            DailyLog object
        """
        # Find stops and segments within this day
        day_stops = []
        for idx, stop_data in enumerate(stops_data):
            arrival = datetime.fromisoformat(stop_data['arrival_time'])
            departure = datetime.fromisoformat(stop_data['departure_time'])

            # Check if stop overlaps with this day
            if arrival < day_end and departure > day_start:
                day_stops.append({
                    'idx': idx,
                    'data': stop_data,
                    'object': stop_objects[idx],
                    'arrival': arrival,
                    'departure': departure
                })

        # Determine start and end locations for this day
        start_location = day_stops[0]['data']['location']['address'] if day_stops else ""
        end_location = day_stops[-1]['data']['location']['address'] if day_stops else ""

        # Create daily log
        daily_log = DailyLog.objects.create(
            route=route,
            log_date=log_date,
            day_number=day_number,
            driver_name=route.trip.user.get_full_name() or route.trip.user.username,
            start_location=start_location,
            end_location=end_location,
        )

        # Generate duty status changes for this day
        self._generate_duty_status_changes(
            daily_log=daily_log,
            day_start=day_start,
            day_end=day_end,
            day_stops=day_stops,
            route=route
        )

        # Calculate and update totals
        self._calculate_daily_totals(daily_log)

        return daily_log

    def _generate_duty_status_changes(
            self,
            daily_log: DailyLog,
            day_start: datetime,
            day_end: datetime,
            day_stops: list,
            route: Route
    ):
        """
        Generate duty status changes for a daily log

        This creates the actual entries that get drawn on the ELD grid

        Args:
            daily_log: DailyLog object
            day_start: Start of 24-hour period
            day_end: End of 24-hour period
            day_stops: Stops occurring during this day
            route: Route object
        """
        sequence = 0
        current_time = max(day_start, route.trip.planned_start_time)

        # If day starts with off-duty (before first activity)
        if day_stops and current_time < day_stops[0]['arrival']:
            DutyStatusChange.objects.create(
                daily_log=daily_log,
                status='off_duty',
                start_time=current_time,
                end_time=day_stops[0]['arrival'],
                duration_minutes=int((day_stops[0]['arrival'] - current_time).total_seconds() / 60),
                location=route.trip.current_location_address,
                sequence=sequence
            )
            sequence += 1
            current_time = day_stops[0]['arrival']

        # Process each stop and driving segment
        for i, stop_info in enumerate(day_stops):
            stop_data = stop_info['data']
            arrival = stop_info['arrival']
            departure = stop_info['departure']

            # Clip times to day boundaries
            arrival = max(arrival, day_start)
            departure = min(departure, day_end)

            # If there's a gap before this stop (driving)
            if current_time < arrival:
                DutyStatusChange.objects.create(
                    daily_log=daily_log,
                    status='driving',
                    start_time=current_time,
                    end_time=arrival,
                    duration_minutes=int((arrival - current_time).total_seconds() / 60),
                    location="En route",
                    sequence=sequence
                )
                sequence += 1

            # Determine stop status
            stop_type = stop_data['stop_type']
            if stop_type == '10hr_break':
                status = 'sleeper_berth'
            elif stop_type == '30min_break':
                status = 'off_duty'
            elif stop_type in ['pickup', 'dropoff', 'fuel']:
                status = 'on_duty_not_driving'
            else:
                status = 'off_duty'

            # Create stop status change
            if arrival < day_end and departure > day_start:
                DutyStatusChange.objects.create(
                    daily_log=daily_log,
                    status=status,
                    start_time=arrival,
                    end_time=departure,
                    duration_minutes=int((departure - arrival).total_seconds() / 60),
                    location=stop_data['location']['address'],
                    location_lat=stop_data['location']['latitude'],
                    location_lng=stop_data['location']['longitude'],
                    remarks=stop_data['description'],
                    sequence=sequence
                )
                sequence += 1

            current_time = departure

        # If day ends with off-duty time
        if current_time < day_end:
            DutyStatusChange.objects.create(
                daily_log=daily_log,
                status='off_duty',
                start_time=current_time,
                end_time=day_end,
                duration_minutes=int((day_end - current_time).total_seconds() / 60),
                location=day_stops[-1]['data']['location']['address'] if day_stops else "",
                sequence=sequence
            )

    def _calculate_daily_totals(self, daily_log: DailyLog):
        """
        Calculate and update daily totals from status changes

        Args:
            daily_log: DailyLog object to update
        """
        status_changes = daily_log.status_changes.all()

        total_off_duty = 0
        total_sleeper = 0
        total_driving = 0
        total_on_duty = 0
        total_miles = 0

        for change in status_changes:
            hours = change.duration_minutes / 60

            if change.status == 'off_duty':
                total_off_duty += hours
            elif change.status == 'sleeper_berth':
                total_sleeper += hours
            elif change.status == 'driving':
                total_driving += hours
                # Estimate miles driven
                total_miles += hours * ELDRules.AVERAGE_SPEED_MPH
            elif change.status == 'on_duty_not_driving':
                total_on_duty += hours

        # Update daily log
        daily_log.total_off_duty_hours = Decimal(str(round(total_off_duty, 2)))
        daily_log.total_sleeper_berth_hours = Decimal(str(round(total_sleeper, 2)))
        daily_log.total_driving_hours = Decimal(str(round(total_driving, 2)))
        daily_log.total_on_duty_hours = Decimal(str(round(total_on_duty, 2)))
        daily_log.total_miles = int(total_miles)
        daily_log.save()