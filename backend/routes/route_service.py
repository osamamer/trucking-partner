"""
Route Service - Generates optimized truck routes with ELD compliance
Uses MapBox Directions API for routing
"""

import requests
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import math


@dataclass
class Location:
    """Represents a geographic location"""
    latitude: float
    longitude: float
    address: str = ""

    def to_coordinates(self) -> str:
        """Returns coordinates in MapBox format: longitude,latitude"""
        return f"{self.longitude},{self.latitude}"


@dataclass
class Stop:
    """Represents a stop on the route"""
    location: Location
    stop_type: str  # 'pickup', 'dropoff', 'fuel', 'rest_break', '30min_break', '10hr_break'
    arrival_time: datetime
    departure_time: datetime
    duration_minutes: int
    description: str = ""


@dataclass
class RouteSegment:
    """Represents a segment of the route between two stops"""
    start_location: Location
    end_location: Location
    distance_miles: float
    duration_minutes: int
    start_time: datetime
    end_time: datetime


class ELDRules:
    """ELD Hours of Service Rules for property-carrying drivers (70/8 day cycle)"""
    MAX_DRIVING_HOURS_PER_DAY = 11
    MAX_ON_DUTY_HOURS_PER_DAY = 14
    MAX_HOURS_PER_CYCLE = 70
    CYCLE_DAYS = 8
    REQUIRED_30MIN_BREAK_AFTER_HOURS = 8
    REQUIRED_OFF_DUTY_HOURS = 10
    AVERAGE_SPEED_MPH = 55  # Conservative highway speed
    FUEL_STOP_INTERVAL_MILES = 1000
    FUEL_STOP_DURATION_MINUTES = 30


class RouteService:
    """Main service for generating ELD-compliant truck routes"""

    def __init__(self, mapbox_api_key: str):
        self.api_key = mapbox_api_key
        self.base_url = "https://api.mapbox.com/directions/v5/mapbox/driving"

    def generate_route(
            self,
            current_location: Location,
            pickup_location: Location,
            dropoff_location: Location,
            current_cycle_hours_used: float,
            start_time: Optional[datetime] = None
    ) -> Dict:
        """
        Generate a complete ELD-compliant route with all stops and breaks
        
        Args:
            current_location: Driver's current position
            pickup_location: Where to pick up the load
            dropoff_location: Where to deliver the load
            current_cycle_hours_used: Hours already used in current 8-day cycle
            start_time: When the trip starts (defaults to now)
            
        Returns:
            Dictionary containing route segments, stops, and ELD compliance info
        """
        if start_time is None:
            start_time = datetime.now()

        # Calculate available hours in cycle
        available_cycle_hours = ELDRules.MAX_HOURS_PER_CYCLE - current_cycle_hours_used

        # Get route data from MapBox
        waypoints = [current_location, pickup_location, dropoff_location]
        route_data = self._fetch_route_from_mapbox(waypoints)

        if not route_data:
            raise Exception("Failed to fetch route from MapBox API")

        # Extract total distance and duration
        total_distance_miles = route_data['distance'] * 0.000621371  # meters to miles
        total_duration_minutes = route_data['duration'] / 60  # seconds to minutes

        # Generate all stops including fuel, breaks, and rest periods
        stops = self._generate_stops(
            waypoints=waypoints,
            total_distance_miles=total_distance_miles,
            start_time=start_time,
            current_cycle_hours_used=current_cycle_hours_used
        )

        # Generate route segments between stops
        segments = self._generate_segments(stops)

        # Calculate ELD compliance metrics
        eld_summary = self._calculate_eld_summary(
            segments=segments,
            stops=stops,
            current_cycle_hours_used=current_cycle_hours_used,
            available_cycle_hours=available_cycle_hours
        )

        # Prepare final route data
        return {
            'total_distance_miles': round(total_distance_miles, 2),
            'total_duration_hours': round(total_duration_minutes / 60, 2),
            'estimated_arrival': stops[-1].arrival_time,
            'stops': [self._stop_to_dict(stop) for stop in stops],
            'segments': [self._segment_to_dict(seg) for seg in segments],
            'eld_summary': eld_summary,
            'mapbox_geometry': route_data['geometry'],  # For drawing on map
            'days_required': eld_summary['days_required']
        }

    def _fetch_route_from_mapbox(self, waypoints: List[Location]) -> Optional[Dict]:
        """
        Fetch route from MapBox Directions API
        
        Args:
            waypoints: List of locations to route through
            
        Returns:
            Route data from MapBox or None if request fails
        """
        # Build coordinates string: lon,lat;lon,lat;lon,lat
        coordinates = ";".join([wp.to_coordinates() for wp in waypoints])

        # MapBox API endpoint
        url = f"{self.base_url}/{coordinates}"

        params = {
            'access_token': self.api_key,
            'geometries': 'geojson',
            'overview': 'full',
            'steps': 'true',
            'annotations': 'distance,duration'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('routes'):
                return data['routes'][0]
            return None

        except requests.exceptions.RequestException as e:
            print(f"MapBox API Error: {e}")
            return None

    def _generate_stops(
            self,
            waypoints: List[Location],
            total_distance_miles: float,
            start_time: datetime,
            current_cycle_hours_used: float
    ) -> List[Stop]:
        """
        Generate all stops including pickup, dropoff, fuel, and mandatory breaks
        
        This is the core ELD compliance logic
        """
        stops = []
        current_time = start_time
        current_driving_hours = 0
        current_on_duty_hours = 0
        current_distance = 0

        # Add pickup stop
        stops.append(Stop(
            location=waypoints[1],
            stop_type='pickup',
            arrival_time=current_time,
            departure_time=current_time + timedelta(hours=1),
            duration_minutes=60,
            description='Load pickup (1 hour)'
        ))
        current_time = stops[-1].departure_time
        current_on_duty_hours += 1

        # Calculate distance from pickup to dropoff
        remaining_distance = total_distance_miles * 0.6  # Approximate distance after pickup

        # Simulate driving with breaks
        while remaining_distance > 0:
            # Calculate how far can drive before needing a break
            hours_until_30min_break = ELDRules.REQUIRED_30MIN_BREAK_AFTER_HOURS - current_driving_hours
            hours_until_daily_limit = ELDRules.MAX_DRIVING_HOURS_PER_DAY - current_driving_hours
            hours_until_on_duty_limit = ELDRules.MAX_ON_DUTY_HOURS_PER_DAY - current_on_duty_hours

            # Determine next break needed
            hours_can_drive = min(
                hours_until_30min_break if current_driving_hours > 0 else float('inf'),
                hours_until_daily_limit,
                hours_until_on_duty_limit
            )

            # Also check fuel stop
            miles_until_fuel = ELDRules.FUEL_STOP_INTERVAL_MILES - (current_distance % ELDRules.FUEL_STOP_INTERVAL_MILES)
            hours_until_fuel = miles_until_fuel / ELDRules.AVERAGE_SPEED_MPH

            # Drive to next stop
            hours_to_drive = min(hours_can_drive, hours_until_fuel, remaining_distance / ELDRules.AVERAGE_SPEED_MPH)
            miles_driven = hours_to_drive * ELDRules.AVERAGE_SPEED_MPH

            current_time += timedelta(hours=hours_to_drive)
            current_driving_hours += hours_to_drive
            current_on_duty_hours += hours_to_drive
            current_distance += miles_driven
            remaining_distance -= miles_driven

            # Determine what stop is needed
            if remaining_distance <= 0:
                # Reached destination
                break
            elif current_distance % ELDRules.FUEL_STOP_INTERVAL_MILES < miles_driven:
                # Need fuel
                stops.append(Stop(
                    location=Location(0, 0, "Fuel Stop (estimated)"),
                    stop_type='fuel',
                    arrival_time=current_time,
                    departure_time=current_time + timedelta(minutes=30),
                    duration_minutes=30,
                    description='Refueling stop'
                ))
                current_time = stops[-1].departure_time
                current_on_duty_hours += 0.5

            elif current_driving_hours >= ELDRules.REQUIRED_30MIN_BREAK_AFTER_HOURS:
                # Need 30-minute break
                stops.append(Stop(
                    location=Location(0, 0, "Rest Stop (estimated)"),
                    stop_type='30min_break',
                    arrival_time=current_time,
                    departure_time=current_time + timedelta(minutes=30),
                    duration_minutes=30,
                    description='Mandatory 30-minute break'
                ))
                current_time = stops[-1].departure_time
                current_driving_hours = 0  # Reset driving hours after break

            elif current_driving_hours >= ELDRules.MAX_DRIVING_HOURS_PER_DAY or \
                    current_on_duty_hours >= ELDRules.MAX_ON_DUTY_HOURS_PER_DAY:
                # Need 10-hour rest period
                stops.append(Stop(
                    location=Location(0, 0, "Rest Area (estimated)"),
                    stop_type='10hr_break',
                    arrival_time=current_time,
                    departure_time=current_time + timedelta(hours=10),
                    duration_minutes=600,
                    description='Mandatory 10-hour off-duty rest period'
                ))
                current_time = stops[-1].departure_time
                current_driving_hours = 0
                current_on_duty_hours = 0

        # Add dropoff stop
        stops.append(Stop(
            location=waypoints[2],
            stop_type='dropoff',
            arrival_time=current_time,
            departure_time=current_time + timedelta(hours=1),
            duration_minutes=60,
            description='Load delivery (1 hour)'
        ))

        return stops

    def _generate_segments(self, stops: List[Stop]) -> List[RouteSegment]:
        """Generate route segments between stops"""
        segments = []

        for i in range(len(stops) - 1):
            start_stop = stops[i]
            end_stop = stops[i + 1]

            duration_minutes = (end_stop.arrival_time - start_stop.departure_time).total_seconds() / 60
            distance_miles = (duration_minutes / 60) * ELDRules.AVERAGE_SPEED_MPH

            segments.append(RouteSegment(
                start_location=start_stop.location,
                end_location=end_stop.location,
                distance_miles=distance_miles,
                duration_minutes=duration_minutes,
                start_time=start_stop.departure_time,
                end_time=end_stop.arrival_time
            ))

        return segments

    def _calculate_eld_summary(
            self,
            segments: List[RouteSegment],
            stops: List[Stop],
            current_cycle_hours_used: float,
            available_cycle_hours: float
    ) -> Dict:
        """Calculate ELD compliance summary"""
        total_driving_hours = sum(seg.duration_minutes for seg in segments) / 60
        total_on_duty_hours = total_driving_hours + sum(
            stop.duration_minutes for stop in stops
            if stop.stop_type in ['pickup', 'dropoff', 'fuel']
        ) / 60

        days_required = math.ceil((stops[-1].arrival_time - stops[0].arrival_time).total_seconds() / (24 * 3600))

        return {
            'total_driving_hours': round(total_driving_hours, 2),
            'total_on_duty_hours': round(total_on_duty_hours, 2),
            'cycle_hours_used': round(current_cycle_hours_used + total_on_duty_hours, 2),
            'cycle_hours_remaining': round(available_cycle_hours - total_on_duty_hours, 2),
            'days_required': days_required,
            'compliance_status': 'compliant' if total_on_duty_hours <= available_cycle_hours else 'exceeded',
            'num_10hr_breaks': len([s for s in stops if s.stop_type == '10hr_break']),
            'num_30min_breaks': len([s for s in stops if s.stop_type == '30min_break']),
            'num_fuel_stops': len([s for s in stops if s.stop_type == 'fuel'])
        }

    def _stop_to_dict(self, stop: Stop) -> Dict:
        """Convert Stop to dictionary"""
        return {
            'location': {
                'latitude': stop.location.latitude,
                'longitude': stop.location.longitude,
                'address': stop.location.address
            },
            'stop_type': stop.stop_type,
            'arrival_time': stop.arrival_time.isoformat(),
            'departure_time': stop.departure_time.isoformat(),
            'duration_minutes': stop.duration_minutes,
            'description': stop.description
        }

    def _segment_to_dict(self, segment: RouteSegment) -> Dict:
        """Convert RouteSegment to dictionary"""
        return {
            'distance_miles': round(segment.distance_miles, 2),
            'duration_minutes': round(segment.duration_minutes, 2),
            'start_time': segment.start_time.isoformat(),
            'end_time': segment.end_time.isoformat()
        }


# Example usage
if __name__ == "__main__":
    # Initialize service with MapBox API key
    service = RouteService(mapbox_api_key="YOUR_MAPBOX_API_KEY")

    # Define locations
    current = Location(latitude=34.0522, longitude=-118.2437, address="Los Angeles, CA")
    pickup = Location(latitude=36.7783, longitude=-119.4179, address="Fresno, CA")
    dropoff = Location(latitude=40.7128, longitude=-74.0060, address="New York, NY")

    # Generate route
    route = service.generate_route(
        current_location=current,
        pickup_location=pickup,
        dropoff_location=dropoff,
        current_cycle_hours_used=20.0,
        start_time=datetime.now()
    )

    print(f"Total Distance: {route['total_distance_miles']} miles")
    print(f"Total Duration: {route['total_duration_hours']} hours")
    print(f"Days Required: {route['days_required']}")
    print(f"Number of Stops: {len(route['stops'])}")
    print(f"\nELD Summary:")
    for key, value in route['eld_summary'].items():
        print(f"  {key}: {value}")