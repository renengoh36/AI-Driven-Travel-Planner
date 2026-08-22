import math
import datetime

EARTH_RADIUS_KM = 6371.0
DAY_START_HOUR = 9                  # itinerary starts at 09:00

# Visit duration (minutes) per attraction category
VISIT_DURATIONS = {
    "nature":     90,    # parks, gardens, beaches
    "food":       60,    # restaurants, hawker stalls, cafes
    "history":   120,    # museums, temples, heritage sites
    "adventure": 150,    # theme parks, water sports, activities
    "shopping":   90,    # malls, markets
    "relaxation": 90,    # spas, wellness centres
}
DEFAULT_VISIT_DURATION  = 90
VISIT_DURATION_MINUTES  = DEFAULT_VISIT_DURATION   # backward-compat alias

# Travel time between consecutive attractions
TRAVEL_SPEED_KMH           = 30   # assumed city travel speed (km/h, with traffic)
MIN_TRAVEL_BUFFER_MINUTES  = 15   # minimum gap even for very close attractions

# Midday lunch break
LUNCH_BREAK_HOUR      = 12
LUNCH_BREAK_MIN       = 30
LUNCH_DURATION_MINUTES = 60

 # Calculates the great-circle distance between two geographic coordinates.
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = EARTH_RADIUS_KM
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

 # Builds a pairwise distance matrix for the selected attractions.
def distance_matrix(attractions: list) -> list:
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

 # Determines an efficient attraction sequence using the nearest-neighbour heuristic.
def nearest_neighbour_route(attractions: list) -> list:
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

# Assigns visit times and order based on attraction duration and travel time.
def assign_time_slots(ordered_attractions: list, day_number: int, visit_order_start: int = 1) -> list:
    items = []
    base_date  = datetime.date.today()
    current_dt = datetime.datetime.combine(base_date, datetime.time(DAY_START_HOUR, 0))
    lunch_dt   = datetime.datetime.combine(base_date, datetime.time(LUNCH_BREAK_HOUR, LUNCH_BREAK_MIN))
    lunch_done = False

    for idx, attraction in enumerate(ordered_attractions):
        order = idx + visit_order_start

        # Insert lunch break if clock has reached 12:30 and not yet taken
        if not lunch_done and current_dt >= lunch_dt:
            current_dt += datetime.timedelta(minutes=LUNCH_DURATION_MINUTES)
            lunch_done = True

        start_dt = current_dt
        duration = VISIT_DURATIONS.get(attraction.get("category", ""), DEFAULT_VISIT_DURATION)
        end_dt   = start_dt + datetime.timedelta(minutes=duration)

        items.append({
            "attraction_id": attraction["attraction_id"],
            "day_number":    day_number,
            "visit_order":   order,
            "start_time":    start_dt.time(),
            "end_time":      end_dt.time(),
        })

        # Travel buffer to the next attraction
        next_idx = idx + 1
        if next_idx < len(ordered_attractions):
            nxt      = ordered_attractions[next_idx]
            dist_km  = haversine(
                attraction.get("latitude",  0.0), attraction.get("longitude", 0.0),
                nxt.get("latitude",         0.0), nxt.get("longitude",        0.0),
            )
            travel   = max(MIN_TRAVEL_BUFFER_MINUTES, int((dist_km / TRAVEL_SPEED_KMH) * 60))
        else:
            travel = 0

        current_dt = end_dt + datetime.timedelta(minutes=travel)

    return items

# Splits attractions across travel days and generates optimised itinerary items.
def build_itinerary_items(selected_attractions: list, travel_days: int) -> list:
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
