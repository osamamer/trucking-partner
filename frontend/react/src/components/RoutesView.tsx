import React from "react";
import { MapPin, Navigation, Clock, ChevronRight } from "lucide-react";
import {MapboxRouteMap} from "./MapBoxRouteMap.tsx";
import type {Trip} from "../App.tsx";

interface RoutesViewProps {
    selectedTrip: Trip;
    onBack: () => void;
}
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
const formatDateTimeShort = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

const RoutesView: React.FC<RoutesViewProps> = ({ selectedTrip, onBack }) => {
    return (
        <div>
            <button
                onClick={onBack}
                className="mb-6 text-orange-400 hover:text-orange-300 flex items-center gap-2"
            >
                ← Back to Trips
            </button>

            {/* Trip Summary */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-orange-500/20 p-6 mb-6">
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
                            {selectedTrip.route.compliance_status === "compliant" ? "✓" : "✗"}
                        </div>
                    </div>
                </div>
            </div>

            {/* Route Map */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-700 p-6 mb-6">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <MapPin className="w-5 h-5 text-orange-400" />
                    Route Map
                </h3>
                <MapboxRouteMap route={selectedTrip.route} />
            </div>

            {/* Route Stops */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-700 p-6">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <Navigation className="w-5 h-5 text-orange-400" />
                    Route Stops
                </h3>
                <div className="space-y-3">
                    {selectedTrip.route.stops.map((stop, idx) => (
                        <div key={stop.sequence}>
                            <div className="bg-gray-700/30 rounded-lg p-4 hover:bg-gray-700/50 transition-all">
                                <div className="flex items-start gap-4">
                                    <div className="text-3xl">{getStopIcon(stop.stop_type)}</div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-start mb-2 flex-wrap gap-2">
                                            <div className="flex-1 min-w-0">
                                                <h4 className="font-bold text-orange-400">{stop.stop_type_display}</h4>
                                                <p className="text-sm text-gray-400 break-words">{stop.location.address}</p>
                                            </div>
                                            <span className="text-xs text-gray-500 flex-shrink-0">
                        Stop {stop.sequence + 1}
                      </span>
                                        </div>
                                        <div className="flex flex-wrap gap-4 text-sm text-gray-400">
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        Arrive: {formatDateTimeShort(stop.arrival_time)}
                      </span>
                                            {stop.duration_minutes > 0 && (
                                                <>
                                                    <span>Duration: {stop.duration_minutes} min</span>
                                                    <span>Depart: {formatDateTimeShort(stop.departure_time)}</span>
                                                </>
                                            )}
                                        </div>
                                        {stop.description && (
                                            <p className="text-sm text-gray-500 mt-2">{stop.description}</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                            {idx < selectedTrip.route.stops.length - 1 && (
                                <div className="ml-8 mt-2 pl-4 border-l-2 border-dashed border-orange-500/30 py-2">
                                    <ChevronRight className="w-4 h-4 text-orange-500/50" />
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default RoutesView;
