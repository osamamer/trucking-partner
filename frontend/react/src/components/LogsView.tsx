import React from "react";
import { AlertCircle } from "lucide-react";
import {ELDGrid} from "./ELDGrid";
import {type Trip, type DailyLog } from "../App.tsx";

interface LogsViewProps {
    selectedTrip: Trip;
    onBack: () => void;
    dailyLogs: DailyLog[];
    loadingLogs: boolean;
}

const LogsView: React.FC<LogsViewProps> = ({ selectedTrip, onBack, dailyLogs, loadingLogs }) => {
    return (
        <div>
            <button
                onClick={onBack}
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

            {loadingLogs ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
                    <p className="text-gray-400 mt-4">Loading daily logs...</p>
                </div>
            ) : dailyLogs.length === 0 ? (
                <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-8 text-center">
                    <AlertCircle className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-gray-300 mb-2">No Daily Logs Found</h3>
                    <p className="text-gray-400">
                        This trip doesn't have any daily logs yet. Generate a route first to create logs.
                    </p>
                </div>
            ) : (
                <div className="space-y-6">
                    {dailyLogs.map((log) => (
                        <div key={log.id} className="space-y-4">
                            <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
                                <div className="flex justify-between items-start mb-4 flex-wrap gap-3">
                                    <div>
                                        <h3 className="text-xl font-bold text-orange-400">Day {log.day_number}</h3>
                                        <p className="text-sm text-gray-400">
                                            {new Date(log.log_date).toLocaleDateString("en-US", {
                                                weekday: "short",
                                                month: "short",
                                                day: "numeric",
                                                year: "numeric",
                                            })}
                                        </p>
                                    </div>
                                    <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm">
                    Compliant
                  </span>
                                </div>

                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                                    <div className="bg-gray-700/30 rounded-lg p-3">
                                        <div className="text-xs text-gray-400 mb-1">Driving</div>
                                        <div className="text-lg font-bold text-orange-400">
                                            {typeof log.total_driving_hours === "number"
                                                ? log.total_driving_hours.toFixed(1)
                                                : log.total_driving_hours}
                                            h
                                        </div>
                                    </div>
                                    <div className="bg-gray-700/30 rounded-lg p-3">
                                        <div className="text-xs text-gray-400 mb-1">On-Duty</div>
                                        <div className="text-lg font-bold text-blue-400">
                                            {typeof log.total_on_duty_hours === "number"
                                                ? log.total_on_duty_hours.toFixed(1)
                                                : log.total_on_duty_hours}
                                            h
                                        </div>
                                    </div>
                                    <div className="bg-gray-700/30 rounded-lg p-3">
                                        <div className="text-xs text-gray-400 mb-1">Off-Duty</div>
                                        <div className="text-lg font-bold text-green-400">
                                            {typeof log.total_off_duty_hours === "number"
                                                ? log.total_off_duty_hours.toFixed(1)
                                                : log.total_off_duty_hours}
                                            h
                                        </div>
                                    </div>
                                    <div className="bg-gray-700/30 rounded-lg p-3">
                                        <div className="text-xs text-gray-400 mb-1">Miles</div>
                                        <div className="text-lg font-bold text-purple-400">
                                            {log.total_miles.toFixed(0)}
                                        </div>
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
                            <ELDGrid log={log} />
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default LogsView;
