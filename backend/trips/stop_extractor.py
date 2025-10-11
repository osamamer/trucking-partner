import json
from typing import List

with open("/home/osama/IdeaProjects/trucking-partner/backend/sample_response.json") as routes_response:
    res = json.loads(routes_response.read())
duration_array = res['routes'][0]['legs'][0]['annotation']['duration']
distance_array = res['routes'][0]['legs'][0]['annotation']['distance']
print(sum(duration_array))
print(sum(distance_array))


def get_fuel_stop_indices(distance_arr: List[int], distance_threshold: int):
    curr_distance = 0
    fuel_stop_indices = []
    for i in range(len(distance_arr)):
        curr_distance += distance_arr[i]
        if curr_distance > distance_threshold:
            fuel_stop_indices.append(i)
            curr_distance = 0
    return fuel_stop_indices

def get_rest_stop_indices(duration_arr: List[int], duration_threshold: int):
    curr_distance = 0
    rest_stop_indices = []
    for i in range(len(duration_arr)):
        curr_distance += duration_arr[i]
        if curr_distance > duration_threshold:
            rest_stop_indices.append(i)
            curr_distance = 0
    return rest_stop_indices




