import {Clock} from "lucide-react";
import type {DailyLog} from "../App.tsx";

export const ELDGrid: React.FC<{ log: DailyLog }> = ({ log }) => {
    const intervals = 96;

    const statusConfig = {
        off_duty: {
            color: 'bg-gray-600',
            label: 'Off Duty',
            row: 0,
            borderColor: 'border-gray-500'
        },
        sleeper: {
            color: 'bg-blue-600',
            label: 'Sleeper Berth',
            row: 1,
            borderColor: 'border-blue-500'
        },
        driving: {
            color: 'bg-green-600',
            label: 'Driving',
            row: 2,
            borderColor: 'border-green-500'
        },
        on_duty: {
            color: 'bg-orange-600',
            label: 'On Duty',
            row: 3,
            borderColor: 'border-orange-500'
        }
    };

    const slots = Array(96).fill(null).map(() => ({
        status: null as string | null,
        overlapMinutes: 0
    }));

    if (log.entries && log.entries.length > 0) {
        log.entries.forEach(entry => {
            const startTime = new Date(entry.start_time);
            const endTime = new Date(entry.end_time);

            const startMinutes = startTime.getHours() * 60 + startTime.getMinutes();
            const endMinutes = endTime.getHours() * 60 + endTime.getMinutes();

            const startSlot = Math.floor(startMinutes / 15);
            const endSlot = Math.ceil(endMinutes / 15);

            for (let slot = startSlot; slot < endSlot && slot < 96; slot++) {
                const slotStartMinutes = slot * 15;
                const slotEndMinutes = (slot + 1) * 15;

                const overlapStart = Math.max(startMinutes, slotStartMinutes);
                const overlapEnd = Math.min(endMinutes, slotEndMinutes);
                const overlapMinutes = overlapEnd - overlapStart;

                if (overlapMinutes > 0 && overlapMinutes > slots[slot].overlapMinutes) {
                    slots[slot] = {
                        status: entry.duty_status,
                        overlapMinutes: overlapMinutes
                    };
                }
            }
        });
    }

    const gridData: Array<{status: string, intervalStart: number, intervalEnd: number}> = [];
    let currentStatus = null;
    let currentStart = 0;

    for (let i = 0; i < 96; i++) {
        if (slots[i].status !== currentStatus) {
            if (currentStatus !== null) {
                gridData.push({
                    status: currentStatus,
                    intervalStart: currentStart,
                    intervalEnd: i
                });
            }
            currentStatus = slots[i].status;
            currentStart = i;
        }
    }

    if (currentStatus !== null) {
        gridData.push({
            status: currentStatus,
            intervalStart: currentStart,
            intervalEnd: 96
        });
    }

    const hourLabels = Array.from({ length: 25 }, (_, i) => {
        const hour = i % 24;
        return hour === 0 ? '12 AM' : hour < 12 ? `${hour} AM` : hour === 12 ? '12 PM' : `${hour - 12} PM`;
    });

    return (
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
            <h4 className="font-bold text-orange-400 mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5" />
                ELD Log Grid - 24 Hour Timeline
            </h4>

            <div className="flex flex-wrap gap-4 mb-4 text-sm">
                {Object.entries(statusConfig).map(([key, config]) => (
                    <div key={key} className="flex items-center gap-2">
                        <div className={`w-4 h-4 ${config.color} rounded`}></div>
                        <span className="text-gray-300">{config.label}</span>
                    </div>
                ))}
            </div>

            <div className="overflow-x-auto">
                <div className="min-w-[800px]">
                    <div className="flex mb-2">
                        <div className="w-32 flex-shrink-0"></div>
                        <div className="flex-1 flex">
                            {hourLabels.map((label, i) => (
                                <div
                                    key={i}
                                    className="flex-1 text-xs text-gray-400 text-center"
                                    style={{ minWidth: `${100 / 24}%` }}
                                >
                                    {i < 24 && label}
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-1">
                        {Object.entries(statusConfig).map(([statusKey, config]) => (
                            <div key={statusKey} className="flex items-center">
                                <div className="w-32 flex-shrink-0 text-sm text-gray-400 pr-4 text-right">
                                    {config.label}
                                </div>

                                <div className="flex-1 relative h-10 bg-gray-900/50 rounded border border-gray-700">
                                    {Array.from({ length: 24 }).map((_, i) => (
                                        <div
                                            key={i}
                                            className="absolute top-0 bottom-0 border-l border-gray-700/50"
                                            style={{ left: `${(i / 24) * 100}%` }}
                                        ></div>
                                    ))}

                                    {gridData
                                        .filter(item => item.status === statusKey)
                                        .map((item, idx) => {
                                            const left = (item.intervalStart / intervals) * 100;
                                            const width = ((item.intervalEnd - item.intervalStart) / intervals) * 100;

                                            return (
                                                <div
                                                    key={idx}
                                                    className={`absolute top-1 bottom-1 ${config.color} ${config.borderColor} border-2 rounded opacity-90 hover:opacity-100 transition-opacity cursor-pointer`}
                                                    style={{
                                                        left: `${left}%`,
                                                        width: `${width}%`
                                                    }}
                                                    title={`${config.label}: ${formatTime(item.intervalStart)} - ${formatTime(item.intervalEnd)}`}
                                                ></div>
                                            );
                                        })}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

const formatTime = (interval: number): string => {
    const totalMinutes = interval * 15;
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    const period = hours < 12 ? 'AM' : 'PM';
    const displayHour = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
    return `${displayHour}:${String(minutes).padStart(2, '0')} ${period}`;
};