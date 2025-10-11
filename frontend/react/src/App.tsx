import React, {useEffect, useRef, useState} from 'react';
import {Truck, MapPin, Clock, AlertCircle, FileText, Plus, ChevronRight, Navigation} from 'lucide-react';
import TripsView from "./components/TripsView.tsx";
import LogsView from "./components/LogsView.tsx";
import RoutesView from "./components/RoutesView.tsx";

export const API_BASE_URL = import.meta.env.MODE === 'production'
    ? '/api'
    : 'http://localhost:8000/api';

export const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

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

export interface RouteData {
    id: number;
    total_distance_miles: number;
    total_duration_hours: number;
    total_driving_hours: number;
    total_on_duty_hours: number;
    compliance_status: string;
    stops: Stop[];
}

export interface Trip {
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

export interface DailyLog {
    id: number;
    day_number: number;
    log_date: string;
    total_driving_hours: string;
    total_on_duty_hours: string;
    total_off_duty_hours: string;
    start_location: string;
    end_location: string;
    total_miles: number;
    entries: LogEntry[];
}

interface LogEntry {
    id: number;
    duty_status: 'off_duty' | 'sleeper' | 'driving' | 'on_duty';
    duty_status_display: string;
    start_time: string;
    end_time: string;
    duration_minutes: number;
    location: string;
    remarks: string;
}





function App() {
    const [activeView, setActiveView] = useState<'trips' | 'create' | 'route' | 'logs'>('trips');
    const [selectedTrip, setSelectedTrip] = useState<Trip | null>(null);
    const [trips, setTrips] = useState<Trip[]>([]);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [errorToast, setErrorToast] = useState<string | null>(null);
    const [dailyLogs, setDailyLogs] = useState<DailyLog[]>([]);
    const [loadingLogs, setLoadingLogs] = useState(false);
    const [generatingRouteForTrip, setGeneratingRouteForTrip] = useState<number | null>(null);
    const [formErrors, setFormErrors] = useState<Record<string, string>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        const fetchTrips = async () => {
            const trips = await getAllTrips();
            setTrips(trips);
        };

        fetchTrips();
    }, []);

    const [formData, setFormData] = useState({
        trip_name: '',
        current_location_address: '',
        pickup_location_address: '',
        dropoff_location_address: '',
        current_cycle_hours_used: '0',
        planned_start_time: ''
    });


    const getAllTrips = async () => {
        const response = await fetch(`${API_BASE_URL}/trips/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        if (!response.ok) throw new Error('Failed to fetch trips');
        return response.json();
    };
    const fetchDailyLogs = async (tripId: number) => {
        setLoadingLogs(true);
        try {
            const response = await fetch(`${API_BASE_URL}/daily-logs/?trip=${tripId}`);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const logs = await response.json();
            console.log('Daily logs fetched:', logs);
            console.log('First log entries:', logs[0]?.entries);
            console.log('Second log entries:', logs[1]?.entries);
            setDailyLogs(logs);
        } catch (error) {
            console.error('Failed to fetch daily logs:', error);
            setDailyLogs([]);
        } finally {
            setLoadingLogs(false);
        }
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
        setFormData({...formData, [e.target.name]: e.target.value});
    };

    const validateForm = () => {
        const errors: Record<string, string> = {};

        // Trip name validation
        if (!formData.trip_name.trim()) {
            errors.trip_name = 'Trip name is required';
        } else if (formData.trip_name.trim().length < 3) {
            errors.trip_name = 'Trip name must be at least 3 characters';
        }

        // Location format validation (City, State or City, State, Country)
        const locationRegex = /^[a-zA-Z\s]+,\s*[a-zA-Z\s]+$/;

        if (!formData.current_location_address.trim()) {
            errors.current_location_address = 'Current location is required';
        } else if (!locationRegex.test(formData.current_location_address.trim())) {
            errors.current_location_address = 'Format: City, State (e.g., "Los Angeles, CA")';
        }

        if (!formData.pickup_location_address.trim()) {
            errors.pickup_location_address = 'Pickup location is required';
        } else if (!locationRegex.test(formData.pickup_location_address.trim())) {
            errors.pickup_location_address = 'Format: City, State (e.g., "Fresno, CA")';
        }

        if (!formData.dropoff_location_address.trim()) {
            errors.dropoff_location_address = 'Dropoff location is required';
        } else if (!locationRegex.test(formData.dropoff_location_address.trim())) {
            errors.dropoff_location_address = 'Format: City, State (e.g., "New York, NY")';
        }

        // Cycle hours validation
        const cycleHours = parseFloat(formData.current_cycle_hours_used);
        if (isNaN(cycleHours) || cycleHours < 0 || cycleHours > 70) {
            errors.current_cycle_hours_used = 'Must be between 0 and 70 hours';
        }

        // Start time validation
        if (!formData.planned_start_time) {
            errors.planned_start_time = 'Planned start time is required';
        } else {
            const startTime = new Date(formData.planned_start_time);
            const now = new Date();
            if (startTime < now) {
                errors.planned_start_time = 'Start time cannot be in the past';
            }
        }

        setFormErrors(errors);
        return Object.keys(errors).length === 0;
    };
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Clear previous errors
        setFormErrors({});

        // Validate form
        if (!validateForm()) {
            return;
        }

        setIsSubmitting(true);

        try {
            const response = await fetch(`${API_BASE_URL}/trips/`, {
                method: 'POST',
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));

                if (response.status === 400 && errorData.errors) {
                    // Backend validation errors
                    setFormErrors(errorData.errors);
                } else {
                    setErrorToast(
                        errorData.message ||
                        errorData.detail ||
                        'Failed to create trip. Please check your information and try again.'
                    );
                    setTimeout(() => setErrorToast(null), 6000);
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const newTrip = await response.json();
            console.log('Trip created successfully:', newTrip);

            // Reset form and close modal
            setFormData({
                trip_name: '',
                current_location_address: '',
                pickup_location_address: '',
                dropoff_location_address: '',
                current_cycle_hours_used: '0',
                planned_start_time: ''
            });
            setFormErrors({});
            const updatedTrips = await getAllTrips();
            setTrips(updatedTrips);
            setShowCreateForm(false);

        } catch (error) {
            console.error('Failed to create trip:', error);
        } finally {
            setIsSubmitting(false);
        }
    };


    const handleGenerateRoute = async (trip: Trip) => {
        console.log('Generating route for trip:', trip.id);

        // Set this trip as currently generating
        setGeneratingRouteForTrip(trip.id);

        try {
            const response = await fetch(`${API_BASE_URL}/trips/${trip.id}/generate_route/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            console.log('Route generation response status:', response.status);
            console.log('Response headers:', response.headers);

            if (!response.ok) {
                let errorMessage = 'The requested route cannot be generated at this time.';

                // Clone the response before reading to avoid "body already read" errors
                const contentType = response.headers.get('content-type');

                try {
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        console.error('Error response JSON:', errorData);
                        errorMessage = errorData.error ||
                            errorData.message ||
                            errorData.detail ||
                            errorMessage;
                    } else {
                        const errorText = await response.text();
                        console.error('Error response text:', errorText);
                        if (errorText) errorMessage = errorText;
                    }
                } catch (parseError) {
                    console.error('Failed to parse error response:', parseError);
                }

                if (response.status === 400) {
                    errorMessage = errorMessage || 'This trip configuration is not feasible. Please check your destinations and try again.';
                } else if (response.status === 404) {
                    errorMessage = 'Trip not found. Please refresh and try again.';
                } else if (response.status === 500) {
                    errorMessage = errorMessage || 'Our route planning service encountered an issue. Please try again in a moment.';
                }

                setErrorToast(errorMessage);
                setTimeout(() => setErrorToast(null), 6000);
                throw new Error(errorMessage);
            }

            const data = await response.json();
            console.log('Route generated successfully:', data);

            // Refresh trips list after successful generation
            const updatedTrips = await getAllTrips();
            setTrips(updatedTrips);

        } catch (error) {
            console.error('Failed to generate route:', error);

            if (!errorToast) {
                const errorMessage = error instanceof Error
                    ? error.message
                    : 'An unexpected error occurred while generating your route.';
                setErrorToast(errorMessage);
                setTimeout(() => setErrorToast(null), 6000);
            }
        } finally {
            // Clear the generating state
            setGeneratingRouteForTrip(null);
        }
    };
    const viewTripRoute = async (trip: Trip) => {
        console.log('=== viewTripRoute called ===');
        console.log('Trip from list:', trip);
        console.log('Trip.route from list:', trip.route);

        try {
            console.log(`Fetching: ${API_BASE_URL}/trips/${trip.id}/`);
            const response = await fetch(`${API_BASE_URL}/trips/${trip.id}/`);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const tripWithRoute = await response.json();
            console.log('Trip from API:', tripWithRoute);
            console.log('Trip.route from API:', tripWithRoute.route);

            if (!tripWithRoute.route) {
                console.log('No route found in API response');
                alert('This trip does not have a route yet. Please generate one first.');
                return;
            }

            console.log('✅ Setting selected trip with route');
            setSelectedTrip(tripWithRoute);
            setActiveView('route');
        } catch (error) {
            console.error('Failed to fetch trip route:', error);
            alert('Failed to load trip route. Check console for details.');
        }
    };

    const viewTripLogs = async (trip: Trip) => {
        setSelectedTrip(trip);
        setActiveView('logs');
        await fetchDailyLogs(trip.id);
    };

    const ErrorToast = () => {
        if (!errorToast) return null;

        return (
            <div className="fixed top-20 right-4 max-w-md animate-slide-in z-[100]">
                <div className="bg-gray-800 rounded-xl shadow-2xl border border-red-500/30 overflow-hidden">
                    <div className="flex items-start p-4 gap-3">
                        <div className="flex-shrink-0">
                            <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
                                <AlertCircle className="w-5 h-5 text-red-400"/>
                            </div>
                        </div>

                        <div className="flex-1 min-w-0">
                            <h3 className="text-sm font-semibold text-white mb-1">
                                Unable to Generate Route
                            </h3>
                            <p className="text-sm text-gray-300 leading-relaxed">
                                {errorToast}
                            </p>
                        </div>

                        <button
                            onClick={() => setErrorToast(null)}
                            className="flex-shrink-0 text-gray-400 hover:text-gray-200 transition-colors"
                        >
                            <span className="text-2xl leading-none">×</span>
                        </button>
                    </div>

                    <div className="h-1 bg-gradient-to-r from-red-500 to-orange-500"/>
                </div>
            </div>
        );
    };
    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-800 via-gray-900 to-gray-800 text-gray-100">
            <ErrorToast/>
            <header className="bg-gray-800/50 backdrop-blur-sm border-b border-orange-500/20 sticky top-0 z-50">
                <div className="container mx-auto px-4 py-4 max-w-full">
                    <div className="flex items-center justify-between flex-wrap gap-4">
                        <div className="flex items-center gap-3">
                            <div className="bg-gradient-to-br from-orange-500 to-orange-600 p-2 rounded-lg">
                                <Truck className="w-6 h-6 text-white"/>
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
                                <Plus className="w-4 h-4"/>
                                New Trip
                            </button>
                        </nav>
                    </div>
                </div>
            </header>

            <main className="container mx-auto px-4 py-8 max-w-full">
                {showCreateForm && (
                    <div
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <div
                            className="bg-gray-800 rounded-2xl border border-orange-500/20 p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
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
                                    <label className="block text-sm font-medium text-gray-300 mb-2">
                                        Trip Name <span className="text-red-400">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        name="trip_name"
                                        value={formData.trip_name}
                                        onChange={handleInputChange}
                                        className={`w-full px-4 py-2 bg-gray-700 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white ${
                                            formErrors.trip_name ? 'border-red-500' : 'border-gray-600'
                                        }`}
                                        placeholder="e.g., LA to NYC Cross-Country"
                                    />
                                    {formErrors.trip_name && (
                                        <p className="text-red-400 text-sm mt-1">{formErrors.trip_name}</p>
                                    )}
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">
                                        Current Location <span className="text-red-400">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        name="current_location_address"
                                        value={formData.current_location_address}
                                        onChange={handleInputChange}
                                        className={`w-full px-4 py-2 bg-gray-700 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white ${
                                            formErrors.current_location_address ? 'border-red-500' : 'border-gray-600'
                                        }`}
                                        placeholder="Los Angeles, CA"
                                    />
                                    {formErrors.current_location_address && (
                                        <p className="text-red-400 text-sm mt-1">{formErrors.current_location_address}</p>
                                    )}
                                    <p className="text-gray-500 text-xs mt-1">Format: City, State</p>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">
                                        Pickup Location <span className="text-red-400">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        name="pickup_location_address"
                                        value={formData.pickup_location_address}
                                        onChange={handleInputChange}
                                        className={`w-full px-4 py-2 bg-gray-700 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white ${
                                            formErrors.pickup_location_address ? 'border-red-500' : 'border-gray-600'
                                        }`}
                                        placeholder="Fresno, CA"
                                    />
                                    {formErrors.pickup_location_address && (
                                        <p className="text-red-400 text-sm mt-1">{formErrors.pickup_location_address}</p>
                                    )}
                                    <p className="text-gray-500 text-xs mt-1">Format: City, State</p>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">
                                        Dropoff Location <span className="text-red-400">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        name="dropoff_location_address"
                                        value={formData.dropoff_location_address}
                                        onChange={handleInputChange}
                                        className={`w-full px-4 py-2 bg-gray-700 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white ${
                                            formErrors.dropoff_location_address ? 'border-red-500' : 'border-gray-600'
                                        }`}
                                        placeholder="New York, NY"
                                    />
                                    {formErrors.dropoff_location_address && (
                                        <p className="text-red-400 text-sm mt-1">{formErrors.dropoff_location_address}</p>
                                    )}
                                    <p className="text-gray-500 text-xs mt-1">Format: City, State</p>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">
                                        Current Cycle Hours Used (0-70) <span className="text-red-400">*</span>
                                    </label>
                                    <input
                                        type="number"
                                        name="current_cycle_hours_used"
                                        value={formData.current_cycle_hours_used}
                                        onChange={handleInputChange}
                                        className={`w-full px-4 py-2 bg-gray-700 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white ${
                                            formErrors.current_cycle_hours_used ? 'border-red-500' : 'border-gray-600'
                                        }`}
                                        min="0"
                                        max="70"
                                        step="0.1"
                                    />
                                    {formErrors.current_cycle_hours_used && (
                                        <p className="text-red-400 text-sm mt-1">{formErrors.current_cycle_hours_used}</p>
                                    )}
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">
                                        Planned Start Time <span className="text-red-400">*</span>
                                    </label>
                                    <input
                                        type="datetime-local"
                                        name="planned_start_time"
                                        value={formData.planned_start_time}
                                        onChange={handleInputChange}
                                        className={`w-full px-4 py-2 bg-gray-700 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-white ${
                                            formErrors.planned_start_time ? 'border-red-500' : 'border-gray-600'
                                        }`}
                                    />
                                    {formErrors.planned_start_time && (
                                        <p className="text-red-400 text-sm mt-1">{formErrors.planned_start_time}</p>
                                    )}
                                </div>

                                <div className="flex gap-3 pt-4">
                                    <button
                                        onClick={handleSubmit}
                                        disabled={isSubmitting}
                                        className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all ${
                                            isSubmitting
                                                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                                                : 'bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:from-orange-600 hover:to-orange-700'
                                        }`}
                                    >
                                        {isSubmitting ? (
                                            <span className="flex items-center justify-center gap-2">
                                <div
                                    className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                                Creating...
                </span>
                                        ) : (
                                            'Create Trip'
                                        )}
                                    </button>
                                    <button
                                        onClick={() => {
                                            setShowCreateForm(false);
                                            setFormErrors({});
                                        }}
                                        disabled={isSubmitting}
                                        className="px-6 py-3 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {activeView === 'trips' && (
                    <TripsView
                        trips={trips}
                        generatingRouteForTrip={generatingRouteForTrip}
                        viewTripRoute={viewTripRoute}
                        viewTripLogs={viewTripLogs}
                        handleGenerateRoute={handleGenerateRoute}
                        getStatusColor={getStatusColor}
                    />
                )}

                {activeView === 'route' && selectedTrip && (
                    <RoutesView
                        selectedTrip={selectedTrip}
                        onBack={() => setActiveView('trips')}
                    />
                )}

                {activeView === 'logs' && selectedTrip && (
                    <LogsView
                        selectedTrip={selectedTrip}
                        onBack={() => setActiveView('trips')}
                        dailyLogs={dailyLogs}
                        loadingLogs={loadingLogs}
                    />
                )}
            </main>
        </div>
    );
}

export default App;