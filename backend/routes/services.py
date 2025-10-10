# routes/services.py

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from django.conf import settings
from django.utils import timezone
from trips.models import Trip
from .models import Route, Stop
from logs.models import DailyLog, LogEntry


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
    """Handles all MapBox API calls"""

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

        response = requests.get(url, params=params)
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
        """
        Find nearest rest area, gas station, or parking near a coordinate
        stop_type: 'rest', 'fuel', 'break'
        """
        # Search terms based on stop type
        search_queries = {
            'rest': 'rest area,truck stop,travel plaza',
            'fuel': 'gas station,truck stop,fuel',
            'break': 'rest area,truck stop,parking,hotel'
        }

        query = search_queries.get(stop_type, 'rest area')

        url = f"{self.BASE_URL}/geocoding/v5/mapbox.places/{query}.json"
        params = {
            'access_token': self.access_token,
            'proximity': f"{lng},{lat}",
            'limit': 5,
            'types': 'poi'
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get('features'):
            # Fallback to just "parking" or estimated location
            return {
                'address': f"Rest Stop (estimated near {lat:.4f}, {lng:.4f})",
                'latitude': lat,
                'longitude': lng,
                'place_id': ''
            }

        # Get the closest result
        feature = data['features'][0]
        coords = feature['geometry']['coordinates']

        return {
            'address': feature.get('place_name', 'Rest Area'),
            'latitude': coords[1],
            'longitude': coords[0],
            'place_id': feature.get('id', '')
        }

    def get_point_along_route(self, geometry: Dict, distance_miles: float, total_distance_miles: float) -> Tuple[float, float]:
        """
        Get lat/lng at a specific distance along the route
        geometry: GeoJSON LineString from MapBox
        distance_miles: how far along the route
        total_distance_miles: total route distance
        """
        coordinates = geometry['coordinates']

        # Calculate the fraction of the route
        fraction = distance_miles / total_distance_miles

        # Simple linear interpolation through the route points
        # For production, you'd want proper distance calculation along the line
        total_points = len(coordinates)
        target_index = int(fraction * (total_points - 1))

        if target_index >= total_points:
            target_index = total_points - 1

        point = coordinates[target_index]
        return point[1], point[0]  # lat, lng


class RouteGenerationService:
    """Main service for generating HOS-compliant routes"""

    def __init__(self, trip: Trip):
        self.trip = trip
        self.mapbox = MapBoxService()
        self.stops = []
        self.current_time = trip.planned_start_time
        self.cumulative_miles = 0
        self.daily_driving_hours = 0
        self.daily_on_duty_hours = 0
        self.hours_since_30min_break = 0
        self.miles_since_fuel = 0

    def generate_route(self) -> Route:
        """Main entry point - generates complete route with all stops"""

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
        """Geocode all addresses"""
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
        """Check if driver has enough hours to complete trip"""
        hours_available = HOSRules.MAX_HOURS_PER_CYCLE - self.trip.current_cycle_hours_used

        # Get rough distance estimate
        waypoints = [
            (self.trip.current_location_latitude, self.trip.current_location_longitude),
            (self.trip.pickup_location_latitude, self.trip.pickup_location_longitude),
            (self.trip.dropoff_location_latitude, self.trip.dropoff_location_longitude)
        ]

        rough_route = self.mapbox.get_route(waypoints)
        estimated_driving_hours = rough_route['distance_miles'] / HOSRules.AVERAGE_SPEED_MPH
        estimated_total_hours = estimated_driving_hours + 2  # pickup + dropoff

        if hours_available < estimated_total_hours:
            self.trip.is_feasible = False
            self.trip.feasibility_message = (
                f"Insufficient hours. Need ~{estimated_total_hours:.1f}h, "
                f"but only {hours_available:.1f}h available in cycle."
            )
            self.trip.save()
            return False

        self.trip.is_feasible = True
        self.trip.total_distance_miles = rough_route['distance_miles']
        self.trip.estimated_duration_hours = rough_route['duration_hours']
        self.trip.save()
        return True

    def _get_base_route(self) -> Dict:
        """Get the base route from MapBox"""
        waypoints = [
            (self.trip.current_location_latitude, self.trip.current_location_longitude),
            (self.trip.pickup_location_latitude, self.trip.pickup_location_longitude),
            (self.trip.dropoff_location_latitude, self.trip.dropoff_location_longitude)
        ]

        return self.mapbox.get_route(waypoints)

    def _generate_stops(self, base_route: Dict):
        """Generate all stops with HOS compliance"""

        # Stop 0: Current location (starting point)
        self._add_stop({
            'type': 'current',
            'address': self.trip.current_location_address,
            'latitude': self.trip.current_location_latitude,
            'longitude': self.trip.current_location_longitude,
            'duration_minutes': 0,
            'description': 'Trip start location'
        })

        # Stop 1: Pickup location
        leg_0 = base_route['legs'][0]
        drive_time_hours = leg_0['duration'] / 3600
        self._advance_time(drive_time_hours, leg_0['distance'] * 0.000621371, is_driving=True)

        self._add_stop({
            'type': 'pickup',
            'address': self.trip.pickup_location_address,
            'latitude': self.trip.pickup_location_latitude,
            'longitude': self.trip.pickup_location_longitude,
            'duration_minutes': HOSRules.PICKUP_DURATION_MINUTES,
            'description': 'Load pickup (1 hour)'
        })

        # Advance time for pickup (on-duty, not driving)
        self._advance_time(HOSRules.PICKUP_DURATION_MINUTES / 60, 0, is_driving=False)

        # Now traverse from pickup to dropoff, inserting stops as needed
        leg_1 = base_route['legs'][1]
        total_leg_distance = leg_1['distance'] * 0.000621371
        total_leg_duration = leg_1['duration'] / 3600

        self._traverse_route_with_stops(
            base_route['geometry'],
            total_leg_distance,
            total_leg_duration
        )

        # Final Stop: Dropoff location
        self._add_stop({
            'type': 'dropoff',
            'address': self.trip.dropoff_location_address,
            'latitude': self.trip.dropoff_location_latitude,
            'longitude': self.trip.dropoff_location_longitude,
            'duration_minutes': HOSRules.DROPOFF_DURATION_MINUTES,
            'description': 'Load delivery (1 hour)'
        })

    def _traverse_route_with_stops(self, geometry: Dict, total_distance: float, total_duration: float):
        """Traverse route from pickup to dropoff, inserting required stops"""

        distance_remaining = total_distance
        distance_covered_in_leg = 0

        while distance_remaining > 0:
            # Check if we need a 30-min break (after 8 hours driving)
            if self.hours_since_30min_break >= HOSRules.REQUIRED_30MIN_BREAK_AFTER_HOURS:
                self._insert_break_stop(geometry, distance_covered_in_leg, total_distance, '30min')
                continue

            # Check if we need a 10-hour rest (max 11h driving or 14h on-duty)
            if (self.daily_driving_hours >= HOSRules.MAX_DRIVING_HOURS_PER_DAY or
                    self.daily_on_duty_hours >= HOSRules.MAX_ON_DUTY_HOURS_PER_DAY):
                self._insert_break_stop(geometry, distance_covered_in_leg, total_distance, '10hr')
                continue

            # Check if we need fuel (every 1000 miles)
            if self.miles_since_fuel >= HOSRules.FUEL_STOP_INTERVAL_MILES:
                self._insert_fuel_stop(geometry, distance_covered_in_leg, total_distance)
                continue

            # Calculate how far we can drive before next stop is needed
            hours_until_break = HOSRules.REQUIRED_30MIN_BREAK_AFTER_HOURS - self.hours_since_30min_break
            hours_until_daily_limit = min(
                HOSRules.MAX_DRIVING_HOURS_PER_DAY - self.daily_driving_hours,
                HOSRules.MAX_ON_DUTY_HOURS_PER_DAY - self.daily_on_duty_hours
            )
            miles_until_fuel = HOSRules.FUEL_STOP_INTERVAL_MILES - self.miles_since_fuel

            hours_can_drive = min(hours_until_break, hours_until_daily_limit)
            miles_can_drive = min(hours_can_drive * HOSRules.AVERAGE_SPEED_MPH, miles_until_fuel, distance_remaining)

            # Drive this segment
            hours_to_drive = miles_can_drive / HOSRules.AVERAGE_SPEED_MPH
            self._advance_time(hours_to_drive, miles_can_drive, is_driving=True)

            distance_covered_in_leg += miles_can_drive
            distance_remaining -= miles_can_drive

    def _insert_break_stop(self, geometry: Dict, distance_along_leg: float, total_leg_distance: float, break_type: str):
        """Insert a 30-min break or 10-hour rest stop"""

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

            # Reset 30-min break timer, but this is on-duty time
            self.current_time += timedelta(minutes=HOSRules.BREAK_30MIN_DURATION)
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

            # Reset daily counters - new day!
            self.current_time += timedelta(minutes=HOSRules.BREAK_10HR_DURATION)
            self.daily_driving_hours = 0
            self.daily_on_duty_hours = 0
            self.hours_since_30min_break = 0

    def _insert_fuel_stop(self, geometry: Dict, distance_along_leg: float, total_leg_distance: float):
        """Insert a fuel stop"""

        # Get location along route
        lat, lng = self.mapbox.get_point_along_route(geometry, distance_along_leg, total_leg_distance)

        # Find nearest gas station
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

        # Fuel stop is on-duty, not driving
        self._advance_time(HOSRules.FUEL_STOP_DURATION_MINUTES / 60, 0, is_driving=False)
        self.miles_since_fuel = 0

    def _add_stop(self, stop_data: Dict):
        """Add a stop to the list"""
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

        self.current_time = departure_time

    def _advance_time(self, hours: float, miles: float, is_driving: bool):
        """Advance time and update counters"""
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
        """Create the Route model"""

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
        """Create Stop models"""

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

    def _generate_daily_logs(self, route: Route):
        """Generate daily log entries for the trip"""

        # Group stops by day
        current_day = 1
        day_start_time = self.stops[0]['arrival_time']
        day_stops = []

        for stop in self.stops:
            # Check if we hit a 10-hour rest (new day boundary)
            if stop['stop_type'] == '10hr_break' and day_stops:
                self._create_daily_log(route, current_day, day_start_time, stop['arrival_time'], day_stops)
                current_day += 1
                day_start_time = stop['departure_time']
                day_stops = []
            else:
                day_stops.append(stop)

        # Create final day log
        if day_stops:
            self._create_daily_log(route, current_day, day_start_time, self.stops[-1]['departure_time'], day_stops)

        # Update trip with days required
        self.trip.days_required = current_day
        self.trip.save()

    def _create_daily_log(self, route: Route, day_number: int, start_time: datetime, end_time: datetime, stops: List[Dict]):
        """Create a single daily log"""

        # Calculate hours
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

            # Calculate driving time to this stop
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


# Main function to call from views
def generate_route_for_trip(trip_id: int) -> Route:
    """
    Generate a complete HOS-compliant route for a trip
    
    Usage:
        route = generate_route_for_trip(trip.id)
    """
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