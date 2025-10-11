import React from "react";
import { MapPin, Navigation, FileText } from "lucide-react";

interface Trip {
    id: number;
    trip_name: string;
    pickup_location_address: string;
    dropoff_location_address: string;
    total_distance_miles?: number;
    days_required?: number;
    status: string;
}

interface TripsViewProps {
    trips: Trip[];
    generatingRouteForTrip: number | null;
    viewTripRoute: (trip: Trip) => void;
    viewTripLogs: (trip: Trip) => void;
    handleGenerateRoute: (trip: Trip) => void;
    getStatusColor: (status: string) => string;
}

const TripsView: React.FC<TripsViewProps> = ({
                                                 trips,
                                                 generatingRouteForTrip,
                                                 viewTripRoute,
                                                 viewTripLogs,
                                                 handleGenerateRoute,
                                                 getStatusColor,
                                             }) => {
    if (trips.length === 0) {
        return (
            <div className="text-center py-20 text-gray-400">
                <h2 className="text-2xl font-semibold mb-2">No trips yet</h2>
                <p className="text-gray-500">Add a new trip to get started!</p>
            </div>
        );
    }

    return (
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
                            <span
                                className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(
                                    trip.status
                                )} flex-shrink-0`}
                            >
                {trip.status}
              </span>
                        </div>

                        <div className="space-y-3 mb-4 flex-grow">
                            <div className="flex items-start gap-2 text-sm">
                                <MapPin className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                                <span className="text-gray-300">
                  {trip.pickup_location_address}
                </span>
                            </div>
                            <div className="flex items-start gap-2 text-sm">
                                <MapPin className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                                <span className="text-gray-300">
                  {trip.dropoff_location_address}
                </span>
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
                                    disabled={generatingRouteForTrip === trip.id}
                                    className={`w-full px-4 py-2 rounded-lg transition-all flex items-center justify-center gap-2 ${
                                        generatingRouteForTrip === trip.id
                                            ? "bg-gray-600 text-gray-400 cursor-not-allowed"
                                            : "bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:from-orange-600 hover:to-orange-700"
                                    }`}
                                >
                                    {generatingRouteForTrip === trip.id ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                                            Generating Route...
                                        </>
                                    ) : (
                                        <>
                                            <Navigation className="w-4 h-4" />
                                            Generate Route
                                        </>
                                    )}
                                </button>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TripsView;
