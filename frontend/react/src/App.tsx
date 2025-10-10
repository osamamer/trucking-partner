import React, {useEffect, useRef, useState} from 'react';
import { Truck, MapPin, Clock, AlertCircle, FileText, Plus, ChevronRight, Navigation } from 'lucide-react';

// const MAPBOX_TOKEN = 'pk.eyJ1Ijoib3NhbWFhbWVyIiwiYSI6ImNtZ2pyMzdyZDBmcGYybHIwM3lhZm94c3MifQ.P8N7prGgak8NWqB1tGdIDw';
const API_BASE_URL = 'http://localhost:8000/api';

// Types
interface Location {
    address: string;
    latitude: number;
    longitude: number;
}

interface Stop {
    sequence: number;
    location: Location;
    stop_type: string;
    stop_type_display: string;
    description: string;
    arrival_time: string;
    departure_time: string;
    duration_minutes: number;
}

interface RouteData {
    id: number;
    total_distance_miles: number;
    total_duration_hours: number;
    total_driving_hours: number;
    total_on_duty_hours: number;
    compliance_status: string;
    stops: Stop[];
}

interface Trip {
    id: number;
    trip_name: string;
    status: string;
    created_at: string;
    pickup_location_address: string;
    dropoff_location_address: string;
    total_distance_miles?: number;
    days_required?: number;
    route?: RouteData;
}

interface DailyLog {
    id: number;
    day_number: number;
    log_date: string;
    total_driving_hours: string;
    total_on_duty_hours: string;
    total_off_duty_hours: string;
    start_location: string;
    end_location: string;
    total_miles: number;
}

const mockTrips: Trip[] = [
    {
        id: 1,
        trip_name: "LA to NYC Cross-Country",
        status: "completed",
        created_at: "2025-10-08T10:00:00Z",
        pickup_location_address: "Fresno, CA",
        dropoff_location_address: "New York, NY",
        total_distance_miles: 2789,
        days_required: 4,
    },
    {
        id: 2,
        trip_name: "Denver to Seattle",
        status: "planning",
        created_at: "2025-10-09T14:30:00Z",
        pickup_location_address: "Denver, CO",
        dropoff_location_address: "Seattle, WA",
        total_distance_miles: 1315,
        days_required: 2,
    }
];

const mockRoute: RouteData = {
    id: 1,
    total_distance_miles: 2789,
    total_duration_hours: 52.3,
    total_driving_hours: 41.2,
    total_on_duty_hours: 45.5,
    compliance_status: "compliant",
    stops: [
        {
            sequence: 0,
            location: { address: "Los Angeles, CA", latitude: 34.05, longitude: -118.24 },
            stop_type: "current",
            stop_type_display: "Starting Point",
            description: "Trip start location",
            arrival_time: "2025-10-10T08:00:00Z",
            departure_time: "2025-10-10T08:00:00Z",
            duration_minutes: 0
        },
        {
            sequence: 1,
            location: { address: "Fresno, CA", latitude: 36.78, longitude: -119.42 },
            stop_type: "pickup",
            stop_type_display: "Pickup",
            description: "Load pickup (1 hour)",
            arrival_time: "2025-10-10T11:30:00Z",
            departure_time: "2025-10-10T12:30:00Z",
            duration_minutes: 60
        },
        {
            sequence: 2,
            location: { address: "Rest Stop (estimated)", latitude: 0, longitude: 0 },
            stop_type: "30min_break",
            stop_type_display: "30-Minute Break",
            description: "Mandatory 30-minute break",
            arrival_time: "2025-10-10T20:30:00Z",
            departure_time: "2025-10-10T21:00:00Z",
            duration_minutes: 30
        },
        {
            sequence: 3,
            location: { address: "Rest Area (estimated)", latitude: 0, longitude: 0 },
            stop_type: "10hr_break",
            stop_type_display: "10-Hour Rest",
            description: "Mandatory 10-hour off-duty rest period",
            arrival_time: "2025-10-11T02:30:00Z",
            departure_time: "2025-10-11T12:30:00Z",
            duration_minutes: 600
        },
        {
            sequence: 4,
            location: { address: "Fuel Stop (estimated)", latitude: 0, longitude: 0 },
            stop_type: "fuel",
            stop_type_display: "Fuel Stop",
            description: "Refueling stop",
            arrival_time: "2025-10-12T06:30:00Z",
            departure_time: "2025-10-12T07:00:00Z",
            duration_minutes: 30
        },
        {
            sequence: 5,
            location: { address: "New York, NY", latitude: 40.71, longitude: -74.00 },
            stop_type: "dropoff",
            stop_type_display: "Dropoff",
            description: "Load delivery (1 hour)",
            arrival_time: "2025-10-13T14:00:00Z",
            departure_time: "2025-10-13T15:00:00Z",
            duration_minutes: 60
        }
    ]
};

const mockDailyLogs: DailyLog[] = [
    {
        id: 1,
        day_number: 1,
        log_date: "2025-10-10",
        total_driving_hours: "11.0",
        total_on_duty_hours: "2.5",
        total_off_duty_hours: "10.5",
        start_location: "Los Angeles, CA",
        end_location: "Rest Area (estimated)",
        total_miles: 605
    },
    {
        id: 2,
        day_number: 2,
        log_date: "2025-10-11",
        total_driving_hours: "10.5",
        total_on_duty_hours: "1.0",
        total_off_duty_hours: "12.5",
        start_location: "Rest Area (estimated)",
        end_location: "Rest Area (estimated)",
        total_miles: 578
    }
];

// MapBox Route Component
const MapboxRouteMap: React.FC<{ route: RouteData }> = ({ route }) => {
    const mapContainer = useRef<HTMLDivElement>(null);
    const map = useRef<any>(null);

    useEffect(() => {
        if (!mapContainer.current || map.current) return;

        // Check if mapboxgl is available
        if (typeof window === 'undefined' || !(window as any).mapboxgl) {
            console.error('Mapbox GL JS not loaded');
            return;
        }

        const mapboxgl = (window as any).mapboxgl;
        mapboxgl.accessToken = MAPBOX_TOKEN;

        // Initialize map
        map.current = new mapboxgl.Map({
            container: mapContainer.current,
            style: 'mapbox://styles/mapbox/dark-v11',
            center: [-98.5795, 39.8283], // Center of US
            zoom: 4
        });

        map.current.on('load', () => {
            // Create route coordinates
            const coordinates = route.stops
                .filter(stop => stop.location.latitude !== 0 && stop.location.longitude !== 0)
                .map(stop => [stop.location.longitude, stop.location.latitude]);

            // Add route line
            map.current.addSource('route', {
                type: 'geojson',
                data: {
                    type: 'Feature',
                    properties: {},
                    geometry: {
                        type: 'LineString',
                        coordinates: coordinates
                    }
                }
            });

            map.current.addLayer({
                id: 'route',
                type: 'line',
                source: 'route',
                layout: {
                    'line-join': 'round',
                    'line-cap': 'round'
                },
                paint: {
                    'line-color': '#f97316',
                    'line-width': 4,
                    'line-opacity': 0.8
                }
            });

            // Add markers for each stop
            route.stops.forEach((stop, index) => {
                if (stop.location.latitude === 0 && stop.location.longitude === 0) return;

                // Create custom marker element
                const el = document.createElement('div');
                el.className = 'custom-marker';
                el.style.width = '32px';
                el.style.height = '32px';
                el.style.borderRadius = '50%';
                el.style.display = 'flex';
                el.style.alignItems = 'center';
                el.style.justifyContent = 'center';
                el.style.fontSize = '18px';
                el.style.cursor = 'pointer';
                el.style.border = '2px solid white';
                el.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)';

                // Set marker color and icon based on stop type
                const markerStyles: Record<string, { bg: string; icon: string }> = {
                    current: { bg: '#3b82f6', icon: '🚛' },
                    pickup: { bg: '#10b981', icon: '📦' },
                    dropoff: { bg: '#ef4444', icon: '🏁' },
                    fuel: { bg: '#f59e0b', icon: '⛽' },
                    '30min_break': { bg: '#8b5cf6', icon: '☕' },
                    '10hr_break': { bg: '#6366f1', icon: '🛏️' }
                };

                const style = markerStyles[stop.stop_type] || { bg: '#6b7280', icon: '📍' };
                el.style.backgroundColor = style.bg;
                el.innerHTML = style.icon;

                // Create popup
                const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(`
                    <div style="color: #1f2937; min-width: 200px;">
                        <h3 style="font-weight: bold; margin-bottom: 4px; color: #f97316;">
                            ${stop.stop_type_display}
                        </h3>
                        <p style="font-size: 14px; margin-bottom: 8px;">${stop.location.address}</p>
                        <p style="font-size: 12px; color: #6b7280;">${stop.description}</p>
                        <p style="font-size: 12px; color: #6b7280; margin-top: 4px;">
                            Arrive: ${new Date(stop.arrival_time).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                })}
                        </p>
                    </div>
                `);

                new mapboxgl.Marker(el)
                    .setLngLat([stop.location.longitude, stop.location.latitude])
                    .setPopup(popup)
                    .addTo(map.current);
            });

            // Fit map to show all markers
            if (coordinates.length > 0) {
                const bounds = coordinates.reduce((bounds, coord) => {
                    return bounds.extend(coord as [number, number]);
                }, new mapboxgl.LngLatBounds(coordinates[0], coordinates[0]));

                map.current.fitBounds(bounds, {
                    padding: 50,
                    maxZoom: 8
                });
            }
        });

        return () => {
            if (map.current) {
                map.current.remove();
                map.current = null;
            }
        };
    }, [route]);

    return (
        <div
            ref={mapContainer}
            className="w-full h-[600px] rounded-xl overflow-hidden border-2 border-orange-500/30"
        />
    );
};

function App() {
    const [activeView, setActiveView] = useState<'trips' | 'create' | 'route' | 'logs'>('trips');
    const [selectedTrip, setSelectedTrip] = useState<Trip | null>(null);
    const [trips] = useState<Trip[]>(mockTrips);
    const [showCreateForm, setShowCreateForm] = useState(false);

    const [formData, setFormData] = useState({
        trip_name: '',
        current_location_address: '',
        pickup_location_address: '',
        dropoff_location_address: '',
        current_cycle_hours_used: '0',
        planned_start_time: ''
    });

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const formatTime = (dateStr: string) => {
        return new Date(dateStr).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getStopIcon = (stopType: string) => {
        const icons: Record<string, string> = {
            pickup: '📦',
            dropoff: '🏁',
            fuel: '⛽',
            '30min_break': '☕',
            '10hr_break': '🛏️'
        };
        return icons[stopType] || '📍';
    };

    const getStatusColor = (status: string) => {
        const colors: Record<string, string> = {
            completed: 'bg-green-500/20 text-green-400 border-green-500/30',
            in_progress: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
            planning: 'bg-blue-500/20 text-blue-400 border-blue-500/30'
        };
        return colors[status] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        console.log('Creating trip:', formData);
        await fetch(API_BASE_URL.concat('/trips/'), {
            method: 'POST',
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                trip_name: formData.trip_name,
                current_location_address: formData.current_location_address,
                pickup_location_address: formData.pickup_location_address,
                dropoff_location_address: formData.dropoff_location_address,
                current_cycle_hours_used: formData.current_cycle_hours_used,
                planned_start_time: formData.planned_start_time,
            })
        })
        setShowCreateForm(false);
    };

    const handleGenerateRoute = async (trip: Trip) => {
        console.log('Generating route for trip:', trip.id);
        await fetch(API_BASE_URL.concat(`/trips/${trip.id}/generate_route/`), {
            method: 'POST',
            headers: {"Content-Type": "application/json"},
        })
    }

    const viewTripRoute = (trip: Trip) => {
        setSelectedTrip({ ...trip, route: mockRoute });
        setActiveView('route');
    };

    const viewTripLogs = (trip: Trip) => {
        setSelectedTrip(trip);
        setActiveView('logs');
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-gray-100">
            <header className="bg-gray-800/50 backdrop-blur-sm border-b border-orange-500/20 sticky top-0 z-50">
                <div className="container mx-auto px-4 py-4 max-w-full">
                    <div className="flex items-center justify-between flex-wrap gap-4">
                        <div className="flex items-center gap-3">
                            <div className="bg-gradient-to-br from-orange-500 to-orange-600 p-2 rounded-lg">
                                <Truck className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold bg-gradient-to-r from-orange-400 to-orange-600 bg-clip-text text-transparent">
                                    Trucking Partner
                                </h1>
                                <p className="text-xs text-gray-400">ELD Compliance & Route Planning</p>
                            </div>
                        </div>
                        <nav className="flex gap-2">
                            <button
                                onClick={() => setActiveView('trips')}
                                className={`px-4 py-2 rounded-lg transition-all ${
                                    activeView === 'trips'
                                        ? 'bg-orange-500 text-white'
                                        : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700'
                                }`}
                            >
                                Trips
                            </button>
                            <button
                                onClick={() => setShowCreateForm(true)}
                                className="px-4 py-2 rounded-lg bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:from-orange-600 hover:to-orange-700 transition-all flex items-center gap-2"
                            >
                                <Plus className="w-4 h-4" />
                                New Trip
                            </button>
                        </nav>
                    </div>
                </div>
            </header>

            <main className="container mx-auto px-4 py-8 max-w-full">
                {showCreateForm && (
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <div className="bg-gray-800 rounded-2xl border border-orange-500/20 p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="flex justify-between items-center mb-6">
                                <h2 className="text-2xl font-bold text-orange-400">Create New Trip</h2>
                                <button
                                    onClick={() => setShowCreateForm(false)}
                                    className="text-gray-400 hover:text-white text-2xl leading-none"
                                >
                                    ×
                                </button>
                            </div>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">Trip Name</label>
                                    <input
                                        type="text"
                                        name="trip_name"
                                        value={formData.trip_name}
                                        onChange={handleInputChange}
                                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white"
                                        placeholder="e.g., LA to NYC Cross-Country"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">Current Location</label>
                                    <input
                                        type="text"
                                        name="current_location_address"
                                        value={formData.current_location_address}
                                        onChange={handleInputChange}
                                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white"
                                        placeholder="Los Angeles, CA"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">Pickup Location</label>
                                    <input
                                        type="text"
                                        name="pickup_location_address"
                                        value={formData.pickup_location_address}
                                        onChange={handleInputChange}
                                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white"
                                        placeholder="Fresno, CA"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">Dropoff Location</label>
                                    <input
                                        type="text"
                                        name="dropoff_location_address"
                                        value={formData.dropoff_location_address}
                                        onChange={handleInputChange}
                                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white"
                                        placeholder="New York, NY"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">Current Cycle Hours Used (0-70)</label>
                                    <input
                                        type="number"
                                        name="current_cycle_hours_used"
                                        value={formData.current_cycle_hours_used}
                                        onChange={handleInputChange}
                                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white"
                                        min="0"
                                        max="70"
                                        step="0.1"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">Planned Start Time</label>
                                    <input
                                        type="datetime-local"
                                        name="planned_start_time"
                                        value={formData.planned_start_time}
                                        onChange={handleInputChange}
                                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white"
                                    />
                                </div>
                                <div className="flex gap-3 pt-4">
                                    <button
                                        onClick={handleSubmit}
                                        className="flex-1 px-6 py-3 bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-lg hover:from-orange-600 hover:to-orange-700 font-medium transition-all"
                                    >
                                        Create Trip
                                    </button>
                                    <button
                                        onClick={() => setShowCreateForm(false)}
                                        className="px-6 py-3 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 font-medium transition-all"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {activeView === 'trips' && (
                    <div>
                        <div className="mb-6">
                            <h2 className="text-3xl font-bold mb-2">Your Trips</h2>
                            <p className="text-gray-400">Manage and view your planned trips</p>
                        </div>
                        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                            {trips.map((trip) => (
                                <div
                                    key={trip.id}
                                    className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 hover:border-orange-500/50 transition-all p-6 group flex flex-col"
                                >
                                    <div className="flex justify-between items-start mb-4 gap-2">
                                        <h3 className="text-xl font-bold text-orange-400 group-hover:text-orange-300 transition-colors flex-1">
                                            {trip.trip_name}
                                        </h3>
                                        <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(trip.status)} flex-shrink-0`}>
                      {trip.status}
                    </span>
                                    </div>
                                    <div className="space-y-3 mb-4 flex-grow">
                                        <div className="flex items-start gap-2 text-sm">
                                            <MapPin className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                                            <span className="text-gray-300">{trip.pickup_location_address}</span>
                                        </div>
                                        <div className="flex items-start gap-2 text-sm">
                                            <MapPin className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                                            <span className="text-gray-300">{trip.dropoff_location_address}</span>
                                        </div>
                                    </div>
                                    {trip.total_distance_miles && (
                                        <div className="flex gap-4 text-sm text-gray-400 mb-4 pb-4 border-b border-gray-700">
                                            <span>🛣️ {trip.total_distance_miles.toLocaleString()} mi</span>
                                            <span>📅 {trip.days_required} days</span>
                                        </div>
                                    )}
                                    <div className="flex gap-2">
                                        {trip.total_distance_miles ? (
                                            <>
                                                <button
                                                    onClick={() => viewTripRoute(trip)}
                                                    className="flex-1 px-4 py-2 bg-orange-500/20 text-orange-400 rounded-lg hover:bg-orange-500/30 transition-all flex items-center justify-center gap-2"
                                                >
                                                    <Navigation className="w-4 h-4" />
                                                    Route
                                                </button>
                                                <button
                                                    onClick={() => viewTripLogs(trip)}
                                                    className="flex-1 px-4 py-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-all flex items-center justify-center gap-2"
                                                >
                                                    <FileText className="w-4 h-4" />
                                                    Logs
                                                </button>
                                            </>
                                        ) : (
                                            <button
                                                onClick={() => handleGenerateRoute(trip)}
                                                className="w-full px-4 py-2 bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-lg hover:from-orange-600 hover:to-orange-700 transition-all flex items-center justify-center gap-2"
                                            >
                                                <Navigation className="w-4 h-4" />
                                                Generate Route
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {activeView === 'route' && selectedTrip?.route && (
                    <div>
                        <button
                            onClick={() => setActiveView('trips')}
                            className="mb-6 text-orange-400 hover:text-orange-300 flex items-center gap-2"
                        >
                            ← Back to Trips
                        </button>
                        <div
                            className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-orange-500/20 p-6 mb-6">
                            <h2 className="text-3xl font-bold mb-4 bg-gradient-to-r from-orange-400 to-orange-600 bg-clip-text text-transparent">
                                {selectedTrip.trip_name}
                            </h2>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="bg-gray-700/50 rounded-lg p-4">
                                    <div className="text-gray-400 text-sm mb-1">Total Distance</div>
                                    <div className="text-2xl font-bold text-orange-400">
                                        {selectedTrip.route.total_distance_miles.toLocaleString()} mi
                                    </div>
                                </div>
                                <div className="bg-gray-700/50 rounded-lg p-4">
                                    <div className="text-gray-400 text-sm mb-1">Driving Hours</div>
                                    <div className="text-2xl font-bold text-blue-400">
                                        {selectedTrip.route.total_driving_hours.toFixed(1)} hrs
                                    </div>
                                </div>
                                <div className="bg-gray-700/50 rounded-lg p-4">
                                    <div className="text-gray-400 text-sm mb-1">Total Duration</div>
                                    <div className="text-2xl font-bold text-purple-400">
                                        {selectedTrip.route.total_duration_hours.toFixed(1)} hrs
                                    </div>
                                </div>
                                <div className="bg-gray-700/50 rounded-lg p-4">
                                    <div className="text-gray-400 text-sm mb-1">Compliance</div>
                                    <div className="text-2xl font-bold text-green-400">
                                        {selectedTrip.route.compliance_status === 'compliant' ? '✓' : '✗'}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-700 p-6 mb-6">
                            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                                <MapPin className="w-5 h-5 text-orange-400"/>
                                Route Map
                            </h3>
                            <MapboxRouteMap route={selectedTrip.route}/>
                        </div>
                        <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-700 p-6">
                            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                                <Navigation className="w-5 h-5 text-orange-400"/>
                                Route Stops
                            </h3>
                            <div className="space-y-3">
                                {selectedTrip.route.stops.map((stop, idx) => (
                                    <div key={stop.sequence}>
                                        <div
                                            className="bg-gray-700/30 rounded-lg p-4 hover:bg-gray-700/50 transition-all">
                                            <div className="flex items-start gap-4">
                                                <div className="text-3xl">{getStopIcon(stop.stop_type)}</div>
                                                <div className="flex-1 min-w-0">
                                                    <div
                                                        className="flex justify-between items-start mb-2 flex-wrap gap-2">
                                                        <div className="flex-1 min-w-0">
                                                            <h4 className="font-bold text-orange-400">{stop.stop_type_display}</h4>
                                                            <p className="text-sm text-gray-400 break-words">{stop.location.address}</p>
                                                        </div>
                                                        <span
                                                            className="text-xs text-gray-500 flex-shrink-0">Stop {stop.sequence + 1}</span>
                                                    </div>
                                                    <div className="flex flex-wrap gap-4 text-sm text-gray-400">
                            <span className="flex items-center gap-1">
                              <Clock className="w-4 h-4"/>
                              Arrive: {formatTime(stop.arrival_time)}
                            </span>
                                                        {stop.duration_minutes > 0 && (
                                                            <span>Duration: {stop.duration_minutes} min</span>
                                                        )}
                                                    </div>
                                                    {stop.description && (
                                                        <p className="text-sm text-gray-500 mt-2">{stop.description}</p>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        {idx < selectedTrip.route.stops.length - 1 && (
                                            <div
                                                className="ml-8 mt-2 pl-4 border-l-2 border-dashed border-orange-500/30 py-2">
                                                <ChevronRight className="w-4 h-4 text-orange-500/50"/>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {activeView === 'logs' && selectedTrip && (
                    <div>
                        <button
                            onClick={() => setActiveView('trips')}
                            className="mb-6 text-orange-400 hover:text-orange-300 flex items-center gap-2"
                        >
                            ← Back to Trips
                        </button>
                        <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-orange-500/20 p-6 mb-6">
                            <h2 className="text-3xl font-bold mb-2 bg-gradient-to-r from-orange-400 to-orange-600 bg-clip-text text-transparent">
                                Daily Logs - {selectedTrip.trip_name}
                            </h2>
                            <p className="text-gray-400">ELD compliance logs for this trip</p>
                        </div>

                        <div className="space-y-4">
                            {mockDailyLogs.map((log) => (
                                <div
                                    key={log.id}
                                    className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6"
                                >
                                    <div className="flex justify-between items-start mb-4 flex-wrap gap-3">
                                        <div>
                                            <h3 className="text-xl font-bold text-orange-400">Day {log.day_number}</h3>
                                            <p className="text-sm text-gray-400">{formatDate(log.log_date)}</p>
                                        </div>
                                        <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm">
                      Compliant
                    </span>
                                    </div>

                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                                        <div className="bg-gray-700/30 rounded-lg p-3">
                                            <div className="text-xs text-gray-400 mb-1">Driving</div>
                                            <div className="text-lg font-bold text-orange-400">{log.total_driving_hours}h</div>
                                        </div>
                                        <div className="bg-gray-700/30 rounded-lg p-3">
                                            <div className="text-xs text-gray-400 mb-1">On-Duty</div>
                                            <div className="text-lg font-bold text-blue-400">{log.total_on_duty_hours}h</div>
                                        </div>
                                        <div className="bg-gray-700/30 rounded-lg p-3">
                                            <div className="text-xs text-gray-400 mb-1">Off-Duty</div>
                                            <div className="text-lg font-bold text-green-400">{log.total_off_duty_hours}h</div>
                                        </div>
                                        <div className="bg-gray-700/30 rounded-lg p-3">
                                            <div className="text-xs text-gray-400 mb-1">Miles</div>
                                            <div className="text-lg font-bold text-purple-400">{log.total_miles}</div>
                                        </div>
                                    </div>

                                    <div className="border-t border-gray-700 pt-4">
                                        <div className="flex flex-col sm:flex-row justify-between gap-2 text-sm">
                      <span className="text-gray-400">
                        Start: <span className="text-gray-300">{log.start_location}</span>
                      </span>
                                            <span className="text-gray-400">
                        End: <span className="text-gray-300">{log.end_location}</span>
                      </span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-6 bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                            <div className="flex items-start gap-3">
                                <AlertCircle className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                                <div>
                                    <h4 className="font-bold text-blue-400 mb-1">ELD Grid Visualization Coming Soon</h4>
                                    <p className="text-sm text-gray-400">
                                        The visual ELD log grid (24-hour timeline with duty status bars) will be implemented next.
                                        Use API endpoint: <code className="bg-gray-700 px-2 py-0.5 rounded text-orange-400 text-xs">
                                        GET /api/daily-logs/&#123;id&#125;/export/
                                    </code>
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}

export default App;