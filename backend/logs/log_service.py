from datetime import datetime, timedelta

def simulate_logs(total_hours):
    logs = []
    remaining = total_hours
    day = 1

    while remaining > 0:
        day_segments = []
        driving_today = min(11, remaining)
        remaining -= driving_today

        # Pickup/dropoff adjustments
        if day == 1:
            day_segments.append({"status": "ON_DUTY", "start": "00:00", "end": "01:00"})
            start_time = datetime.strptime("01:00", "%H:%M")
        else:
            start_time = datetime.strptime("00:00", "%H:%M")

        drive_end = start_time + timedelta(hours=driving_today)
        day_segments.append({
            "status": "DRIVING",
            "start": start_time.strftime("%H:%M"),
            "end": drive_end.strftime("%H:%M")
        })

        # Add remaining on-duty and off-duty periods
        if (drive_end - start_time).seconds / 3600 < 14:
            on_duty_end = start_time + timedelta(hours=14)
            day_segments.append({
                "status": "ON_DUTY",
                "start": drive_end.strftime("%H:%M"),
                "end": on_duty_end.strftime("%H:%M")
            })

        day_segments.append({
            "status": "OFF_DUTY",
            "start": "14:00",
            "end": "24:00"
        })

        logs.append({
            "day": day,
            "segments": day_segments
        })
        day += 1

    return logs
