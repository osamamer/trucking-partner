# routes/services.py
import json
import zoneinfo
from asyncio import timeout
from collections import defaultdict
from webbrowser import open_new

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from django.conf import settings
from django.utils import timezone
from trips.models import Trip
from .models import Route, Stop
from logs.models import DailyLog, LogEntry
import logging
from logs.models import LogEntry

logger = logging.getLogger(__name__)

# HOS Rules Configuration
class HOSRules:
    MAX_DRIVING_HOURS_PER_DAY = 11
    MAX_ON_DUTY_HOURS_PER_DAY = 14
    MAX_HOURS_PER_CYCLE = 70
    CYCLE_DAYS = 8
    REQUIRED_30MIN_BREAK_AFTER_HOURS = 8
    REQUIRED_OFF_DUTY_HOURS = 10
    AVERAGE_SPEED_MPH = 55
    FUEL_STOP_INTERVAL_MILES = 1000
    FUEL_STOP_DURATION_MINUTES = 30
    BREAK_30MIN_DURATION = 30
    BREAK_10HR_DURATION = 600
    PICKUP_DURATION_MINUTES = 60
    DROPOFF_DURATION_MINUTES = 60


class MapBoxService:
    # todo proper bug handling for api errors

    BASE_URL = "https://api.mapbox.com"

    def __init__(self):
        self.access_token = settings.MAPBOX_ACCESS_TOKEN

    def geocode_address(self, address: str) -> Tuple[float, float]:
        """Convert address to lat/lng"""
        url = f"{self.BASE_URL}/geocoding/v5/mapbox.places/{address}.json"
        params = {
            'access_token': self.access_token,
            'limit': 1
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get('features'):
            raise ValueError(f"Could not geocode address: {address}")

        coordinates = data['features'][0]['geometry']['coordinates']
        return coordinates[1], coordinates[0]  # lat, lng

    def get_route(self, waypoints: List[Tuple[float, float]]) -> Dict:
        """
        Get route between multiple waypoints
        Returns: distance (miles), duration (hours), geometry
        """
        # Format: lng,lat;lng,lat;lng,lat
        coordinates = ';'.join([f"{lng},{lat}" for lat, lng in waypoints])

        url = f"{self.BASE_URL}/directions/v5/mapbox/driving/{coordinates}"
        params = {
            'access_token': self.access_token,
            'geometries': 'geojson',
            'overview': 'full',
            'steps': 'true'
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get('routes'):
            raise ValueError("No route found")

        route = data['routes'][0]

        # Convert meters to miles, seconds to hours
        distance_miles = route['distance'] * 0.000621371
        duration_hours = route['duration'] / 3600

        return {
            'distance_miles': distance_miles,
            'duration_hours': duration_hours,
            'geometry': route['geometry'],
            'legs': route['legs']
        }

    def find_nearest_stop_location(self, lat: float, lng: float, stop_type: str) -> Optional[Dict]:

        # Find nearest rest area, gas station, or parking near a coordinate

        search_strategies = {
            'rest': [
                'truck stop',
                'rest area',
                'travel center',
                'parking'
            ],
            'fuel': [
                'gas station',
                'fuel',
                'truck stop',
                'service station'
            ],
            'break': [
                'hotel',
                'motel',
                'truck stop',
                'rest area'
            ]
        }

        queries = search_strategies.get(stop_type, ['truck stop'])

        # Try each query until we find results
        for query in queries:
            url = f"{self.BASE_URL}/geocoding/v5/mapbox.places/{query}.json"
            params = {
                'access_token': self.access_token,
                'proximity': f"{lng},{lat}",
                'limit': 1,
                'types': 'poi',  # Points of Interest
                'language': 'en'
            }
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                logger.info(f"Mapbox search for '{query}' at ({lat}, {lng}): {len(data.get('features', []))} results")

                if data.get('features') and len(data['features']) > 0:
                    feature = data['features'][0]
                    coords = feature['geometry']['coordinates']
                    place_name = feature.get('place_name', feature.get('text', 'Unknown location'))

                    logger.info(f"Found place: {place_name}")

                    return {
                        'address': place_name,
                        'latitude': coords[1],
                        'longitude': coords[0],
                        'place_id': feature.get('id', '')
                    }

            except requests.exceptions.RequestException as e:
                logger.error(f"Mapbox API error for query '{query}': {e}")
                continue

        #  try reverse geocoding to at least get city/state
        try:
            url = f"{self.BASE_URL}/geocoding/v5/mapbox.places/{lng},{lat}.json"
            params = {
                'access_token': self.access_token,
                'types': 'place,locality',
                'limit': 1
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get('features'):
                location_name = data['features'][0].get('place_name', 'Unknown location')
                logger.info(f"Using reverse geocoded location: {location_name}")

                stop_type_label = {
                    'rest': 'Rest Stop',
                    'fuel': 'Fuel Stop',
                    'break': 'Rest Area'
                }.get(stop_type, 'Stop')

                return {
                    'address': f"{stop_type_label} near {location_name}",
                    'latitude': lat,
                    'longitude': lng,
                    'place_id': ''
                }

        except Exception as e:
            logger.error(f"Reverse geocoding failed: {e}")

        # Ultimate fallback
        logger.warning(f"No location found for {stop_type} at ({lat}, {lng}), using coordinates")
        return {
            'address': f"Rest Stop (estimated near {lat:.4f}, {lng:.4f})",
            'latitude': lat,
            'longitude': lng,
            'place_id': ''
        }

    def get_point_along_route(self, geometry: Dict, distance_miles: float, total_distance_miles: float) -> Tuple[float, float]:
        # Get lat/lng at a specific distance along the route
        coordinates = geometry['coordinates']

        fraction = distance_miles / total_distance_miles  # Calculate the fraction of the route

        total_points = len(coordinates)
        target_index = int(fraction * (total_points - 1))

        if target_index >= total_points:
            target_index = total_points - 1

        point = coordinates[target_index]
        return point[1], point[0]  # lat, lng


class RouteGenerationService:

    def __init__(self, trip: Trip):
        self.trip = trip
        self.mapbox = MapBoxService()  # No parameters needed
        self.stops = []

        # Set timezone based on user location (Jordan = Asia/Amman)
        self.timezone = zoneinfo.ZoneInfo('Asia/Amman')

        # Ensure start time is timezone-aware
        if trip.planned_start_time.tzinfo is None:
            # Naive datetime - assume it's in local time and make it aware
            from django.utils import timezone as django_tz
            self.current_time = django_tz.make_aware(trip.planned_start_time, timezone=self.timezone)
        else:
            # Already aware - convert to local timezone
            self.current_time = trip.planned_start_time.astimezone(self.timezone)

        # Store initial state
        self.cumulative_miles = 0
        self.daily_driving_hours = 0
        self.daily_on_duty_hours = 0
        self.hours_since_30min_break = 0
        self.miles_since_fuel = 0

    def generate_route(self) -> Route:
        # Step 1: Geocode all addresses if not already done
        self._geocode_locations()

        # Step 2: Check feasibility
        if not self._check_feasibility():
            raise ValueError(self.trip.feasibility_message)

        # Step 3: Get base route from MapBox
        base_route = self._get_base_route()
        # Step 4: Generate all stops with HOS compliance
        self._generate_stops(base_route)

        # Step 5: Create Route model
        route = self._create_route(base_route)

        # Step 6: Create Stop models
        self._create_stops(route)

        # Step 7: Generate daily logs
        self._generate_daily_logs(route)

        return route

    def _geocode_locations(self):
        if not self.trip.current_location_latitude:
            lat, lng = self.mapbox.geocode_address(self.trip.current_location_address)
            self.trip.current_location_latitude = lat
            self.trip.current_location_longitude = lng

        if not self.trip.pickup_location_latitude:
            lat, lng = self.mapbox.geocode_address(self.trip.pickup_location_address)
            self.trip.pickup_location_latitude = lat
            self.trip.pickup_location_longitude = lng

        if not self.trip.dropoff_location_latitude:
            lat, lng = self.mapbox.geocode_address(self.trip.dropoff_location_address)
            self.trip.dropoff_location_latitude = lat
            self.trip.dropoff_location_longitude = lng

        self.trip.save()

    def _check_feasibility(self) -> bool:
        # TODO: If start time is after his cycle is over, allow it to be feasible
        hours_available = HOSRules.MAX_HOURS_PER_CYCLE - self.trip.current_cycle_hours_used

        waypoints = [
            (self.trip.current_location_latitude, self.trip.current_location_longitude),
            (self.trip.pickup_location_latitude, self.trip.pickup_location_longitude),
            (self.trip.dropoff_location_latitude, self.trip.dropoff_location_longitude)
        ]

        route_result = self.mapbox.get_route(waypoints)
        duration = route_result['duration_hours']
        if hours_available < route_result['duration_hours']:
            self.trip.is_feasible = False
            self.trip.feasibility_message = (
                f"Insufficient hours. Need ~{duration:.1f}h, "
                f"but only {hours_available:.1f}h available in cycle."
            )
            self.trip.save()
            return False

        self.trip.is_feasible = True
        self.trip.total_distance_miles = route_result['distance_miles']
        self.trip.estimated_duration_hours = route_result['duration_hours']
        self.trip.save()
        return True

    def _get_base_route(self) -> Dict:
        waypoints = [
            (self.trip.current_location_latitude, self.trip.current_location_longitude),
            (self.trip.pickup_location_latitude, self.trip.pickup_location_longitude),
            (self.trip.dropoff_location_latitude, self.trip.dropoff_location_longitude)
        ]

        return self.mapbox.get_route(waypoints)

    def _generate_stops(self, base_route: Dict):

        self._add_stop({
            'type': 'current',
            'address': self.trip.current_location_address,
            'latitude': self.trip.current_location_latitude,
            'longitude': self.trip.current_location_longitude,
            'duration_minutes': 0,
            'description': 'Trip start location'
        })

        leg_0 = base_route['legs'][0]
        drive_time_hours = leg_0['duration'] / 3600
        drive_distance_miles = leg_0['distance'] * 0.000621371

        # Advance time for driving to pickup
        self.current_time += timedelta(hours=drive_time_hours)
        self.cumulative_miles += drive_distance_miles
        self.daily_driving_hours += drive_time_hours
        self.daily_on_duty_hours += drive_time_hours
        self.hours_since_30min_break += drive_time_hours
        self.miles_since_fuel += drive_distance_miles

        self._add_stop({
            'type': 'pickup',
            'address': self.trip.pickup_location_address,
            'latitude': self.trip.pickup_location_latitude,
            'longitude': self.trip.pickup_location_longitude,
            'duration_minutes': HOSRules.PICKUP_DURATION_MINUTES,
            'description': 'Load pickup (1 hour)'
        })

        # Now traverse from pickup to dropoff, inserting stops as needed
        leg_1 = base_route['legs'][1]
        total_leg_distance = leg_1['distance'] * 0.000621371
        total_leg_duration = leg_1['duration'] / 3600

        self._traverse_route_with_stops(
            base_route['geometry'],
            total_leg_distance,
            total_leg_duration
        )

        self._add_stop({
            'type': 'dropoff',
            'address': self.trip.dropoff_location_address,
            'latitude': self.trip.dropoff_location_latitude,
            'longitude': self.trip.dropoff_location_longitude,
            'duration_minutes': HOSRules.DROPOFF_DURATION_MINUTES,
            'description': 'Load delivery (1 hour)'
        })

    def _traverse_route_with_stops(self, geometry: Dict, total_distance: float, total_duration: float):

        distance_remaining = total_distance
        distance_covered_in_leg = 0

        while distance_remaining > 0:
            if self.hours_since_30min_break >= HOSRules.REQUIRED_30MIN_BREAK_AFTER_HOURS:
                self._insert_break_stop(geometry, distance_covered_in_leg, total_distance, '30min')
                continue

            if (self.daily_driving_hours >= HOSRules.MAX_DRIVING_HOURS_PER_DAY or
                    self.daily_on_duty_hours >= HOSRules.MAX_ON_DUTY_HOURS_PER_DAY):
                self._insert_break_stop(geometry, distance_covered_in_leg, total_distance, '10hr')
                continue

            if self.miles_since_fuel >= HOSRules.FUEL_STOP_INTERVAL_MILES:
                self._insert_fuel_stop(geometry, distance_covered_in_leg, total_distance)
                continue

            hours_until_break = HOSRules.REQUIRED_30MIN_BREAK_AFTER_HOURS - self.hours_since_30min_break
            hours_until_daily_limit = min(
                HOSRules.MAX_DRIVING_HOURS_PER_DAY - self.daily_driving_hours,
                HOSRules.MAX_ON_DUTY_HOURS_PER_DAY - self.daily_on_duty_hours
            )
            miles_until_fuel = HOSRules.FUEL_STOP_INTERVAL_MILES - self.miles_since_fuel

            hours_can_drive = min(hours_until_break, hours_until_daily_limit)
            miles_can_drive = min(hours_can_drive * HOSRules.AVERAGE_SPEED_MPH, miles_until_fuel, distance_remaining)

            hours_to_drive = miles_can_drive / HOSRules.AVERAGE_SPEED_MPH

            self.current_time += timedelta(hours=hours_to_drive)
            self.cumulative_miles += miles_can_drive
            self.daily_driving_hours += hours_to_drive
            self.daily_on_duty_hours += hours_to_drive
            self.hours_since_30min_break += hours_to_drive
            self.miles_since_fuel += miles_can_drive

            distance_covered_in_leg += miles_can_drive
            distance_remaining -= miles_can_drive

    def _insert_break_stop(self, geometry: Dict, distance_along_leg: float, total_leg_distance: float, break_type: str):

        # Get location along route
        lat, lng = self.mapbox.get_point_along_route(geometry, distance_along_leg, total_leg_distance)

        # Find nearest rest area
        stop_location = self.mapbox.find_nearest_stop_location(lat, lng, 'rest')

        if break_type == '30min':
            self._add_stop({
                'type': '30min_break',
                'address': stop_location['address'],
                'latitude': stop_location['latitude'],
                'longitude': stop_location['longitude'],
                'duration_minutes': HOSRules.BREAK_30MIN_DURATION,
                'description': 'Mandatory 30-minute break',
                'place_id': stop_location.get('place_id', '')
            })

            self.daily_on_duty_hours += HOSRules.BREAK_30MIN_DURATION / 60
            self.hours_since_30min_break = 0

        else:  # 10-hour rest
            self._add_stop({
                'type': '10hr_break',
                'address': stop_location['address'],
                'latitude': stop_location['latitude'],
                'longitude': stop_location['longitude'],
                'duration_minutes': HOSRules.BREAK_10HR_DURATION,
                'description': 'Mandatory 10-hour off-duty rest period',
                'place_id': stop_location.get('place_id', '')
            })

            # Reset daily counters - new day starts after this rest
            # Note: current_time already advanced by _add_stop to departure_time
            self.daily_driving_hours = 0
            self.daily_on_duty_hours = 0
            self.hours_since_30min_break = 0

    def _insert_fuel_stop(self, geometry: Dict, distance_along_leg: float, total_leg_distance: float):

        lat, lng = self.mapbox.get_point_along_route(geometry, distance_along_leg, total_leg_distance)
        stop_location = self.mapbox.find_nearest_stop_location(lat, lng, 'fuel')

        self._add_stop({
            'type': 'fuel',
            'address': stop_location['address'],
            'latitude': stop_location['latitude'],
            'longitude': stop_location['longitude'],
            'duration_minutes': HOSRules.FUEL_STOP_DURATION_MINUTES,
            'description': 'Refueling stop',
            'place_id': stop_location.get('place_id', '')
        })

        self.miles_since_fuel = 0

    def _add_stop(self, stop_data: Dict):
        arrival_time = self.current_time
        departure_time = arrival_time + timedelta(minutes=stop_data['duration_minutes'])

        self.stops.append({
            'sequence': len(self.stops),
            'stop_type': stop_data['type'],
            'address': stop_data['address'],
            'latitude': stop_data['latitude'],
            'longitude': stop_data['longitude'],
            'arrival_time': arrival_time,
            'departure_time': departure_time,
            'duration_minutes': stop_data['duration_minutes'],
            'description': stop_data['description'],
            'place_id': stop_data.get('place_id', ''),
            'cumulative_miles': self.cumulative_miles
        })

        # Update current_time to departure time
        self.current_time = departure_time

        # Update on-duty hours for non-driving activities
        if stop_data['type'] in ['pickup', 'dropoff', 'fuel']:
            hours = stop_data['duration_minutes'] / 60
            self.daily_on_duty_hours += hours

    def _advance_time(self, hours: float, miles: float, is_driving: bool):
        self.current_time += timedelta(hours=hours)
        self.cumulative_miles += miles

        if is_driving:
            self.daily_driving_hours += hours
            self.daily_on_duty_hours += hours
            self.hours_since_30min_break += hours
            self.miles_since_fuel += miles
        else:
            # On-duty but not driving (loading, fueling)
            self.daily_on_duty_hours += hours

    def _create_route(self, base_route: Dict) -> Route:

        total_driving_hours = sum(
            (s['departure_time'] - s['arrival_time']).total_seconds() / 3600
            for s in self.stops if s['stop_type'] in ['current', 'pickup', 'dropoff']
        ) + base_route['duration_hours']

        total_on_duty_hours = total_driving_hours + sum(
            s['duration_minutes'] / 60
            for s in self.stops if s['stop_type'] in ['pickup', 'dropoff', 'fuel']
        )

        total_duration = (self.stops[-1]['departure_time'] - self.stops[0]['arrival_time']).total_seconds() / 3600
        total_off_duty = total_duration - total_on_duty_hours

        route = Route.objects.create(
            trip=self.trip,
            total_distance_miles=self.cumulative_miles,
            total_duration_hours=total_duration,
            total_driving_hours=total_driving_hours,
            total_on_duty_hours=total_on_duty_hours,
            total_off_duty_hours=total_off_duty,
            compliance_status='compliant',
            mapbox_route_geometry=base_route['geometry']
        )

        return route

    def _create_stops(self, route: Route):

        for i, stop_data in enumerate(self.stops):
            miles_from_previous = 0
            if i > 0:
                miles_from_previous = stop_data['cumulative_miles'] - self.stops[i-1]['cumulative_miles']

            Stop.objects.create(
                route=route,
                sequence=stop_data['sequence'],
                stop_type=stop_data['stop_type'],
                address=stop_data['address'],
                latitude=stop_data['latitude'],
                longitude=stop_data['longitude'],
                place_id=stop_data.get('place_id', ''),
                arrival_time=stop_data['arrival_time'],
                departure_time=stop_data['departure_time'],
                duration_minutes=stop_data['duration_minutes'],
                description=stop_data['description'],
                miles_from_previous=miles_from_previous,
                cumulative_miles=stop_data['cumulative_miles']
            )

    from collections import defaultdict

    def _generate_daily_logs(self, route: Route):
        if not self.stops:
            return

        stops_by_date = defaultdict(list)
        drives_by_date = defaultdict(list)

        for i in range(len(self.stops)):
            stop = self.stops[i]
            arrival = stop['arrival_time']
            departure = stop['departure_time']
            tzinfo = arrival.tzinfo

            start_date = arrival.date()
            end_date = departure.date()

            current_date = start_date
            while current_date <= end_date:
                day_start = datetime.combine(current_date, datetime.min.time())
                day_end = datetime.combine(current_date, datetime.max.time())
                if tzinfo:
                    day_start = day_start.replace(tzinfo=tzinfo)
                    day_end = day_end.replace(tzinfo=tzinfo)

                day_arrival = max(arrival, day_start)
                day_departure = min(departure, day_end)

                stops_by_date[current_date].append({
                    'original_stop': stop,
                    'stop_index': i,
                    'day_arrival': day_arrival,
                    'day_departure': day_departure,
                    'day_duration_hours': (day_departure - day_arrival).total_seconds() / 3600.0
                })

                current_date = current_date + timedelta(days=1)

            if i > 0:
                prev_stop = self.stops[i - 1]
                drive_start = prev_stop['departure_time']
                drive_end = stop['arrival_time']

                if drive_end > drive_start:
                    drive_start_date = drive_start.date()
                    drive_end_date = drive_end.date()

                    current_date = drive_start_date
                    while current_date <= drive_end_date:
                        day_start = datetime.combine(current_date, datetime.min.time())
                        day_end = datetime.combine(current_date, datetime.max.time())
                        if tzinfo:
                            day_start = day_start.replace(tzinfo=tzinfo)
                            day_end = day_end.replace(tzinfo=tzinfo)

                        day_drive_start = max(drive_start, day_start)
                        day_drive_end = min(drive_end, day_end)

                        if day_drive_end > day_drive_start:
                            drives_by_date[current_date].append({
                                'from_stop_index': i - 1,
                                'to_stop_index': i,
                                'day_start': day_drive_start,
                                'day_end': day_drive_end,
                                'from_stop': prev_stop,
                                'to_stop': stop
                            })

                        current_date = current_date + timedelta(days=1)

        sorted_dates = sorted(set(list(stops_by_date.keys()) + list(drives_by_date.keys())))
        for day_number, log_date in enumerate(sorted_dates, start=1):
            self._create_daily_log_for_date(
                route,
                day_number,
                log_date,
                stops_by_date.get(log_date, []),
                drives_by_date.get(log_date, [])
            )

        self.trip.days_required = len(sorted_dates)
        self.trip.save()

    def _create_daily_log_for_date(self, route: Route, day_number: int, log_date, day_stop_info: List[Dict], day_drive_info: List[Dict]):
        tzinfo = None
        if day_stop_info:
            tzinfo = day_stop_info[0]['day_arrival'].tzinfo
        elif day_drive_info:
            tzinfo = day_drive_info[0]['day_start'].tzinfo

        day_start = datetime.combine(log_date, datetime.min.time())
        day_end = datetime.combine(log_date, datetime.max.time())
        if tzinfo:
            day_start = day_start.replace(tzinfo=tzinfo)
            day_end = day_end.replace(tzinfo=tzinfo)

        day_entries = sorted(day_stop_info, key=lambda x: x['day_arrival'])

        driving_hours = 0.0
        on_duty_not_driving_hours = 0.0
        off_duty_hours = 0.0
        total_miles = 0.0

        for drive in day_drive_info:
            drive_duration = (drive['day_end'] - drive['day_start']).total_seconds() / 3600.0
            driving_hours += drive_duration

            global_drive_duration = (drive['to_stop']['arrival_time'] - drive['from_stop']['departure_time']).total_seconds() / 3600.0
            if global_drive_duration > 0:
                drive_distance = drive['to_stop']['cumulative_miles'] - drive['from_stop']['cumulative_miles']
                total_miles += drive_distance * (drive_duration / global_drive_duration)

        for entry in day_entries:
            orig = entry['original_stop']
            stop_duration = entry['day_duration_hours']
            stype = orig['stop_type']

            if stype in ['pickup', 'dropoff', 'fuel']:
                on_duty_not_driving_hours += stop_duration
            elif stype in ['30min_break', '10hr_break']:
                off_duty_hours += stop_duration
            else:
                off_duty_hours += stop_duration

        total_on_duty_hours = driving_hours + on_duty_not_driving_hours
        total_off_duty_hours = 24.0 - total_on_duty_hours

        daily_log = DailyLog.objects.create(
            trip=self.trip,
            day_number=day_number,
            log_date=log_date,
            total_driving_hours=round(driving_hours, 2),
            total_on_duty_hours=round(total_on_duty_hours, 2),
            total_off_duty_hours=round(total_off_duty_hours, 2),
            start_location=day_entries[0]['original_stop']['address'] if day_entries else 'N/A',
            end_location=day_entries[-1]['original_stop']['address'] if day_entries else 'N/A',
            total_miles=round(total_miles, 1),
            is_compliant=True
        )

        self._create_log_entries_for_day(daily_log, day_start, day_end, day_entries, day_drive_info)

    def _create_log_entries_for_day(self, daily_log, day_start, day_end, day_entries, day_drives):
        entries = []
        current_time = day_start

        all_events = []

        for drive in day_drives:
            all_events.append({
                'type': 'drive',
                'time': drive['day_start'],
                'data': drive
            })

        for entry in day_entries:
            all_events.append({
                'type': 'stop',
                'time': entry['day_arrival'],
                'data': entry
            })

        all_events.sort(key=lambda x: x['time'])

        for event in all_events:
            if event['type'] == 'drive':
                drive = event['data']

                if drive['day_start'] > current_time:
                    entries.append({
                        'duty_status': 'off_duty',
                        'start_time': current_time,
                        'end_time': drive['day_start'],
                        'location': entries[-1]['location'] if entries else drive['from_stop']['address'],
                        'latitude': entries[-1].get('latitude') if entries else drive['from_stop'].get('latitude'),
                        'longitude': entries[-1].get('longitude') if entries else drive['from_stop'].get('longitude'),
                        'remarks': 'Off duty'
                    })
                    current_time = drive['day_start']

                entries.append({
                    'duty_status': 'driving',
                    'start_time': current_time,
                    'end_time': drive['day_end'],
                    'location': f"En route to {drive['to_stop']['address']}",
                    'latitude': drive['to_stop'].get('latitude'),
                    'longitude': drive['to_stop'].get('longitude'),
                    'remarks': f"Driving from {drive['from_stop']['address']}"
                })
                current_time = drive['day_end']

            else:
                entry = event['data']
                arrival = entry['day_arrival']
                departure = entry['day_departure']
                orig = entry['original_stop']

                if arrival > current_time:
                    entries.append({
                        'duty_status': 'off_duty',
                        'start_time': current_time,
                        'end_time': arrival,
                        'location': entries[-1]['location'] if entries else orig['address'],
                        'latitude': entries[-1].get('latitude') if entries else orig.get('latitude'),
                        'longitude': entries[-1].get('longitude') if entries else orig.get('longitude'),
                        'remarks': 'Off duty'
                    })
                    current_time = arrival

                if departure > current_time:
                    duty_status_map = {
                        'pickup': 'on_duty',
                        'dropoff': 'on_duty',
                        'fuel': 'on_duty',
                        '30min_break': 'off_duty',
                        '10hr_break': 'sleeper',
                        'current': 'off_duty'
                    }
                    duty_status = duty_status_map.get(orig['stop_type'], 'off_duty')

                    entries.append({
                        'duty_status': duty_status,
                        'start_time': current_time,
                        'end_time': departure,
                        'location': orig['address'],
                        'latitude': orig.get('latitude'),
                        'longitude': orig.get('longitude'),
                        'remarks': orig.get('description', '')
                    })
                    current_time = departure

        if current_time < day_end:
            entries.append({
                'duty_status': 'off_duty',
                'start_time': current_time,
                'end_time': day_end,
                'location': entries[-1]['location'] if entries else 'N/A',
                'latitude': entries[-1].get('latitude') if entries else None,
                'longitude': entries[-1].get('longitude') if entries else None,
                'remarks': 'Off duty'
            })

        for i, entry_data in enumerate(entries):
            start = entry_data['start_time']
            end = entry_data['end_time']

            if end <= start:
                logger.error(f"Invalid entry: {start} -> {end}")
                continue

            if i > 0:
                prev_end = entries[i - 1]['end_time']
                if start < prev_end:
                    logger.error(f"OVERLAP: {start} < {prev_end}")
                    continue
                elif start > prev_end:
                    gap = (start - prev_end).total_seconds()
                    logger.error(f"GAP: {gap}s between entries")

            duration_min = int((end - start).total_seconds() / 60)

            LogEntry.objects.create(
                daily_log=daily_log,
                duty_status=entry_data['duty_status'],
                start_time=start,
                end_time=end,
                duration_minutes=duration_min,
                location=entry_data.get('location', ''),
                latitude=entry_data.get('latitude'),
                longitude=entry_data.get('longitude'),
                remarks=entry_data.get('remarks', '')
            )

    def _create_daily_log(self, route: Route, day_number: int, start_time: datetime, end_time: datetime, stops: List[Dict]):
        driving_hours = 0
        on_duty_hours = 0
        off_duty_hours = 0
        total_miles = 0

        for i, stop in enumerate(stops):
            duration_hours = stop['duration_minutes'] / 60

            if stop['stop_type'] in ['pickup', 'dropoff', 'fuel']:
                on_duty_hours += duration_hours
            elif stop['stop_type'] in ['30min_break', '10hr_break']:
                off_duty_hours += duration_hours

            if i > 0:
                prev_stop = stops[i-1]
                drive_time = (stop['arrival_time'] - prev_stop['departure_time']).total_seconds() / 3600
                driving_hours += drive_time
                on_duty_hours += drive_time
                total_miles += stop['cumulative_miles'] - prev_stop['cumulative_miles']

        # Remaining time is off-duty
        total_day_hours = (end_time - start_time).total_seconds() / 3600
        off_duty_hours = total_day_hours - on_duty_hours

        DailyLog.objects.create(
            trip=self.trip,
            day_number=day_number,
            log_date=start_time.date(),
            total_driving_hours=round(driving_hours, 2),
            total_on_duty_hours=round(on_duty_hours, 2),
            total_off_duty_hours=round(off_duty_hours, 2),
            start_location=stops[0]['address'],
            end_location=stops[-1]['address'],
            total_miles=round(total_miles, 1),
            is_compliant=True
        )


#  function to call from views
def generate_route_for_trip(trip_id: int) -> Route:

    try:
        trip = Trip.objects.get(id=trip_id)
        service = RouteGenerationService(trip)
        route = service.generate_route()

        trip.status = 'planning'
        trip.save()

        return route

    except Trip.DoesNotExist:
        raise ValueError(f"Trip {trip_id} not found")
    except Exception as e:
        # Log error and update trip
        trip = Trip.objects.get(id=trip_id)
        trip.is_feasible = False
        trip.feasibility_message = f"Error generating route: {str(e)}"
        trip.save()
        raise