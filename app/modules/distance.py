
import math
import datetime


EARTH_RADIUS_KM = 6371.0
VISIT_DURATION_MINUTES = 90       # assumed time at each attraction
DAY_START_HOUR = 9                 # itinerary starts at 09:00


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns great-circle distance in km between two points."""
    r = EARTH_RADIUS_KM
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distance_matrix(attractions: list) -> list:
    """
    Builds a symmetric n×n matrix of pairwise Haversine distances.
    attractions: list of dicts with 'latitude' and 'longitude'.
    Returns a 2D list.
    """
    n = len(attractions)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine(
                attractions[i]["latitude"], attractions[i]["longitude"],
                attractions[j]["latitude"], attractions[j]["longitude"],
            )
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


def nearest_neighbour_route(attractions: list) -> list:
    """
    Nearest-neighbour heuristic for TSP.
    Starts at index 0, greedily picks the closest unvisited attraction.
    Returns the ordered list of attraction dicts.
    """
    if not attractions:
        return []
    if len(attractions) == 1:
        return attractions[:]

    dist = distance_matrix(attractions)
    n = len(attractions)
    visited = [False] * n
    route_indices = [0]
    visited[0] = True

    for _ in range(n - 1):
        current = route_indices[-1]
        nearest = None
        nearest_dist = float("inf")
        for j in range(n):
            if not visited[j] and dist[current][j] < nearest_dist:
                nearest_dist = dist[current][j]
                nearest = j
        route_indices.append(nearest)
        visited[nearest] = True

    return [attractions[i] for i in route_indices]


def assign_time_slots(ordered_attractions: list, day_number: int, visit_order_start: int = 1) -> list:
    """
    Assigns start_time, end_time, day_number, and visit_order to each attraction.
    Returns a list of dicts ready to write to ITINERARY_ITEMS.
    """
    items = []
    current_time = datetime.time(DAY_START_HOUR, 0)

    for order, attraction in enumerate(ordered_attractions, start=visit_order_start):
        start_dt = datetime.datetime.combine(datetime.date.today(), current_time)
        end_dt = start_dt + datetime.timedelta(minutes=VISIT_DURATION_MINUTES)

        items.append({
            "attraction_id": attraction["attraction_id"],
            "day_number": day_number,
            "visit_order": order,
            "start_time": current_time,
            "end_time": end_dt.time(),
        })

        # Next attraction starts right after (no travel buffer — keep simple for MVP)
        current_time = end_dt.time()

    return items


def build_itinerary_items(selected_attractions: list, travel_days: int) -> list:
    """
    Full pipeline: takes a flat list of selected attractions, splits them
    across travel_days with route optimisation per day.

    Returns a flat list of item dicts (day_number, attraction_id, visit_order,
    start_time, end_time) ready to insert into ITINERARY_ITEMS.
    """
    if not selected_attractions:
        return []

    # Split attractions evenly across days
    per_day = math.ceil(len(selected_attractions) / travel_days)
    all_items = []

    for day in range(1, travel_days + 1):
        start_idx = (day - 1) * per_day
        day_attractions = selected_attractions[start_idx: start_idx + per_day]
        if not day_attractions:
            break
        optimised = nearest_neighbour_route(day_attractions)
        items = assign_time_slots(optimised, day_number=day)
        all_items.extend(items)

    return all_items
