import math

def get_activity_grid(activities):
    grid = ['OFF_DUTY'] * 96 # Set all 96 15-min slots in a day to OFF_DUTY as a default
    for activity in activities:
        start_minutes = activity.start_time.hour * 60 + activity.start_time.minute
        start_idx = start_minutes // 15

        end_minutes = activity.end_time.hour * 60 + activity.end_time.minute
        end_idx = math.ceil(end_minutes / 15) if activity.end_time else start_idx # Don't log activity if not yet finished

        start_idx = max(0, start_idx)
        end_idx = min(96, end_idx)

        for i in range(start_idx, end_idx):
            grid[i] = activity.type

    return grid
