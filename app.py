from flask import Flask, render_template, request, jsonify
import requests
import math
import json
import os
ORS_API_KEY = os.environ.get("ORS_API_KEY", "")


app = Flask(__name__)

# OpenRouteService API Key and Base URL
ORS_API_KEY = "5b3ce3597851110001cf6248159698df886c401eb4c33836da4c121d"
ORS_BASE_URL = "https://api.openrouteservice.org"

# ─────────────────────────────────────────────
# CAR DATABASE  (make → model → specs)
# Specs sourced from EPA / manufacturer data
# ─────────────────────────────────────────────
CAR_DATABASE = {
    "Toyota": {
        "Camry": {
            "weight": 1560, "drag_coefficient": 0.28, "frontal_area": 2.24,
            "rolling_resistance": 0.010, "engine_displacement": 2.5,
            "idle_rate": 0.55, "base_consumption": 0.072, "optimal_speed": 80,
            "accel_cost": 0.012, "efficiency": 0.26, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "Corolla": {
            "weight": 1355, "drag_coefficient": 0.27, "frontal_area": 2.19,
            "rolling_resistance": 0.010, "engine_displacement": 2.0,
            "idle_rate": 0.48, "base_consumption": 0.064, "optimal_speed": 80,
            "accel_cost": 0.010, "efficiency": 0.27, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "RAV4": {
            "weight": 1735, "drag_coefficient": 0.33, "frontal_area": 2.65,
            "rolling_resistance": 0.012, "engine_displacement": 2.5,
            "idle_rate": 0.72, "base_consumption": 0.085, "optimal_speed": 75,
            "accel_cost": 0.018, "efficiency": 0.25, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Prius": {
            "weight": 1420, "drag_coefficient": 0.24, "frontal_area": 2.16,
            "rolling_resistance": 0.009, "engine_displacement": 1.8,
            "idle_rate": 0.10, "base_consumption": 0.042, "optimal_speed": 85,
            "accel_cost": 0.006, "efficiency": 0.38, "fuel_type": "hybrid",
            "category": "sedan"
        },
        "Highlander": {
            "weight": 2041, "drag_coefficient": 0.35, "frontal_area": 2.90,
            "rolling_resistance": 0.013, "engine_displacement": 3.5,
            "idle_rate": 0.95, "base_consumption": 0.105, "optimal_speed": 70,
            "accel_cost": 0.022, "efficiency": 0.23, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Tacoma": {
            "weight": 1895, "drag_coefficient": 0.40, "frontal_area": 3.10,
            "rolling_resistance": 0.013, "engine_displacement": 3.5,
            "idle_rate": 0.90, "base_consumption": 0.110, "optimal_speed": 65,
            "accel_cost": 0.025, "efficiency": 0.22, "fuel_type": "gasoline",
            "category": "truck"
        },
    },
    "Honda": {
        "Civic": {
            "weight": 1278, "drag_coefficient": 0.28, "frontal_area": 2.19,
            "rolling_resistance": 0.010, "engine_displacement": 1.5,
            "idle_rate": 0.45, "base_consumption": 0.060, "optimal_speed": 80,
            "accel_cost": 0.009, "efficiency": 0.28, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "Accord": {
            "weight": 1498, "drag_coefficient": 0.27, "frontal_area": 2.26,
            "rolling_resistance": 0.010, "engine_displacement": 1.5,
            "idle_rate": 0.52, "base_consumption": 0.068, "optimal_speed": 80,
            "accel_cost": 0.011, "efficiency": 0.27, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "CR-V": {
            "weight": 1590, "drag_coefficient": 0.33, "frontal_area": 2.68,
            "rolling_resistance": 0.012, "engine_displacement": 1.5,
            "idle_rate": 0.65, "base_consumption": 0.082, "optimal_speed": 75,
            "accel_cost": 0.016, "efficiency": 0.26, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Pilot": {
            "weight": 2005, "drag_coefficient": 0.36, "frontal_area": 2.88,
            "rolling_resistance": 0.013, "engine_displacement": 3.5,
            "idle_rate": 0.92, "base_consumption": 0.108, "optimal_speed": 70,
            "accel_cost": 0.021, "efficiency": 0.23, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Ridgeline": {
            "weight": 1997, "drag_coefficient": 0.39, "frontal_area": 3.05,
            "rolling_resistance": 0.013, "engine_displacement": 3.5,
            "idle_rate": 0.88, "base_consumption": 0.108, "optimal_speed": 65,
            "accel_cost": 0.024, "efficiency": 0.22, "fuel_type": "gasoline",
            "category": "truck"
        },
    },
    "Ford": {
        "F-150": {
            "weight": 2065, "drag_coefficient": 0.41, "frontal_area": 3.32,
            "rolling_resistance": 0.013, "engine_displacement": 3.5,
            "idle_rate": 1.00, "base_consumption": 0.120, "optimal_speed": 65,
            "accel_cost": 0.028, "efficiency": 0.21, "fuel_type": "gasoline",
            "category": "truck"
        },
        "Mustang": {
            "weight": 1696, "drag_coefficient": 0.35, "frontal_area": 2.32,
            "rolling_resistance": 0.011, "engine_displacement": 5.0,
            "idle_rate": 0.80, "base_consumption": 0.105, "optimal_speed": 90,
            "accel_cost": 0.022, "efficiency": 0.22, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "Explorer": {
            "weight": 2021, "drag_coefficient": 0.38, "frontal_area": 2.92,
            "rolling_resistance": 0.013, "engine_displacement": 2.3,
            "idle_rate": 0.88, "base_consumption": 0.105, "optimal_speed": 70,
            "accel_cost": 0.022, "efficiency": 0.23, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Escape": {
            "weight": 1607, "drag_coefficient": 0.34, "frontal_area": 2.65,
            "rolling_resistance": 0.012, "engine_displacement": 1.5,
            "idle_rate": 0.65, "base_consumption": 0.083, "optimal_speed": 75,
            "accel_cost": 0.016, "efficiency": 0.25, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Bronco": {
            "weight": 1975, "drag_coefficient": 0.45, "frontal_area": 3.15,
            "rolling_resistance": 0.014, "engine_displacement": 2.3,
            "idle_rate": 0.92, "base_consumption": 0.115, "optimal_speed": 65,
            "accel_cost": 0.026, "efficiency": 0.21, "fuel_type": "gasoline",
            "category": "suv"
        },
    },
    "BMW": {
        "3 Series": {
            "weight": 1540, "drag_coefficient": 0.26, "frontal_area": 2.22,
            "rolling_resistance": 0.010, "engine_displacement": 2.0,
            "idle_rate": 0.55, "base_consumption": 0.072, "optimal_speed": 85,
            "accel_cost": 0.013, "efficiency": 0.26, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "5 Series": {
            "weight": 1795, "drag_coefficient": 0.25, "frontal_area": 2.31,
            "rolling_resistance": 0.010, "engine_displacement": 2.0,
            "idle_rate": 0.60, "base_consumption": 0.082, "optimal_speed": 85,
            "accel_cost": 0.015, "efficiency": 0.26, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "X5": {
            "weight": 2175, "drag_coefficient": 0.33, "frontal_area": 2.85,
            "rolling_resistance": 0.012, "engine_displacement": 3.0,
            "idle_rate": 0.95, "base_consumption": 0.110, "optimal_speed": 75,
            "accel_cost": 0.023, "efficiency": 0.24, "fuel_type": "gasoline",
            "category": "suv"
        },
        "X3": {
            "weight": 1845, "drag_coefficient": 0.31, "frontal_area": 2.66,
            "rolling_resistance": 0.012, "engine_displacement": 2.0,
            "idle_rate": 0.78, "base_consumption": 0.092, "optimal_speed": 75,
            "accel_cost": 0.019, "efficiency": 0.25, "fuel_type": "gasoline",
            "category": "suv"
        },
    },
    "Mercedes-Benz": {
        "C-Class": {
            "weight": 1605, "drag_coefficient": 0.24, "frontal_area": 2.21,
            "rolling_resistance": 0.010, "engine_displacement": 2.0,
            "idle_rate": 0.58, "base_consumption": 0.075, "optimal_speed": 85,
            "accel_cost": 0.013, "efficiency": 0.26, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "E-Class": {
            "weight": 1905, "drag_coefficient": 0.23, "frontal_area": 2.28,
            "rolling_resistance": 0.010, "engine_displacement": 2.0,
            "idle_rate": 0.65, "base_consumption": 0.088, "optimal_speed": 85,
            "accel_cost": 0.016, "efficiency": 0.26, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "GLE": {
            "weight": 2215, "drag_coefficient": 0.34, "frontal_area": 2.88,
            "rolling_resistance": 0.012, "engine_displacement": 3.0,
            "idle_rate": 1.00, "base_consumption": 0.115, "optimal_speed": 75,
            "accel_cost": 0.024, "efficiency": 0.23, "fuel_type": "gasoline",
            "category": "suv"
        },
    },
    "Volkswagen": {
        "Golf": {
            "weight": 1317, "drag_coefficient": 0.29, "frontal_area": 2.20,
            "rolling_resistance": 0.010, "engine_displacement": 1.4,
            "idle_rate": 0.45, "base_consumption": 0.062, "optimal_speed": 80,
            "accel_cost": 0.010, "efficiency": 0.27, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "Tiguan": {
            "weight": 1655, "drag_coefficient": 0.33, "frontal_area": 2.66,
            "rolling_resistance": 0.012, "engine_displacement": 2.0,
            "idle_rate": 0.68, "base_consumption": 0.086, "optimal_speed": 75,
            "accel_cost": 0.017, "efficiency": 0.25, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Passat": {
            "weight": 1492, "drag_coefficient": 0.25, "frontal_area": 2.27,
            "rolling_resistance": 0.010, "engine_displacement": 2.0,
            "idle_rate": 0.52, "base_consumption": 0.070, "optimal_speed": 82,
            "accel_cost": 0.012, "efficiency": 0.27, "fuel_type": "gasoline",
            "category": "sedan"
        },
    },
    "Chevrolet": {
        "Silverado": {
            "weight": 2136, "drag_coefficient": 0.42, "frontal_area": 3.38,
            "rolling_resistance": 0.013, "engine_displacement": 5.3,
            "idle_rate": 1.05, "base_consumption": 0.125, "optimal_speed": 65,
            "accel_cost": 0.030, "efficiency": 0.21, "fuel_type": "gasoline",
            "category": "truck"
        },
        "Equinox": {
            "weight": 1614, "drag_coefficient": 0.33, "frontal_area": 2.66,
            "rolling_resistance": 0.012, "engine_displacement": 1.5,
            "idle_rate": 0.65, "base_consumption": 0.083, "optimal_speed": 75,
            "accel_cost": 0.016, "efficiency": 0.25, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Tahoe": {
            "weight": 2518, "drag_coefficient": 0.40, "frontal_area": 3.20,
            "rolling_resistance": 0.014, "engine_displacement": 5.3,
            "idle_rate": 1.20, "base_consumption": 0.145, "optimal_speed": 65,
            "accel_cost": 0.035, "efficiency": 0.20, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Malibu": {
            "weight": 1470, "drag_coefficient": 0.29, "frontal_area": 2.22,
            "rolling_resistance": 0.010, "engine_displacement": 1.5,
            "idle_rate": 0.50, "base_consumption": 0.068, "optimal_speed": 80,
            "accel_cost": 0.011, "efficiency": 0.27, "fuel_type": "gasoline",
            "category": "sedan"
        },
    },
    "Subaru": {
        "Outback": {
            "weight": 1657, "drag_coefficient": 0.33, "frontal_area": 2.60,
            "rolling_resistance": 0.011, "engine_displacement": 2.5,
            "idle_rate": 0.68, "base_consumption": 0.087, "optimal_speed": 75,
            "accel_cost": 0.017, "efficiency": 0.25, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Forester": {
            "weight": 1590, "drag_coefficient": 0.34, "frontal_area": 2.64,
            "rolling_resistance": 0.012, "engine_displacement": 2.5,
            "idle_rate": 0.65, "base_consumption": 0.085, "optimal_speed": 75,
            "accel_cost": 0.017, "efficiency": 0.25, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Impreza": {
            "weight": 1349, "drag_coefficient": 0.30, "frontal_area": 2.20,
            "rolling_resistance": 0.010, "engine_displacement": 2.0,
            "idle_rate": 0.48, "base_consumption": 0.068, "optimal_speed": 78,
            "accel_cost": 0.011, "efficiency": 0.26, "fuel_type": "gasoline",
            "category": "sedan"
        },
    },
    "Hyundai": {
        "Elantra": {
            "weight": 1322, "drag_coefficient": 0.27, "frontal_area": 2.18,
            "rolling_resistance": 0.010, "engine_displacement": 2.0,
            "idle_rate": 0.46, "base_consumption": 0.063, "optimal_speed": 80,
            "accel_cost": 0.010, "efficiency": 0.27, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "Tucson": {
            "weight": 1615, "drag_coefficient": 0.33, "frontal_area": 2.65,
            "rolling_resistance": 0.012, "engine_displacement": 2.5,
            "idle_rate": 0.67, "base_consumption": 0.085, "optimal_speed": 75,
            "accel_cost": 0.017, "efficiency": 0.25, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Sonata": {
            "weight": 1495, "drag_coefficient": 0.25, "frontal_area": 2.23,
            "rolling_resistance": 0.010, "engine_displacement": 2.5,
            "idle_rate": 0.52, "base_consumption": 0.070, "optimal_speed": 82,
            "accel_cost": 0.012, "efficiency": 0.27, "fuel_type": "gasoline",
            "category": "sedan"
        },
    },
    "Kia": {
        "Sportage": {
            "weight": 1576, "drag_coefficient": 0.33, "frontal_area": 2.64,
            "rolling_resistance": 0.012, "engine_displacement": 2.5,
            "idle_rate": 0.66, "base_consumption": 0.084, "optimal_speed": 75,
            "accel_cost": 0.016, "efficiency": 0.25, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Sorento": {
            "weight": 1835, "drag_coefficient": 0.34, "frontal_area": 2.78,
            "rolling_resistance": 0.012, "engine_displacement": 2.5,
            "idle_rate": 0.78, "base_consumption": 0.095, "optimal_speed": 72,
            "accel_cost": 0.020, "efficiency": 0.24, "fuel_type": "gasoline",
            "category": "suv"
        },
        "K5": {
            "weight": 1477, "drag_coefficient": 0.27, "frontal_area": 2.20,
            "rolling_resistance": 0.010, "engine_displacement": 2.5,
            "idle_rate": 0.51, "base_consumption": 0.070, "optimal_speed": 82,
            "accel_cost": 0.012, "efficiency": 0.27, "fuel_type": "gasoline",
            "category": "sedan"
        },
    },
    "Tesla": {
        "Model 3": {
            "weight": 1611, "drag_coefficient": 0.23, "frontal_area": 2.22,
            "rolling_resistance": 0.009, "engine_displacement": 0,
            "idle_rate": 0.02, "base_consumption": 0.155, "optimal_speed": 90,
            "accel_cost": 0.020, "efficiency": 0.92, "fuel_type": "electric",
            "category": "sedan", "kwh_per_100km": 15.5
        },
        "Model Y": {
            "weight": 1979, "drag_coefficient": 0.23, "frontal_area": 2.66,
            "rolling_resistance": 0.009, "engine_displacement": 0,
            "idle_rate": 0.03, "base_consumption": 0.170, "optimal_speed": 90,
            "accel_cost": 0.022, "efficiency": 0.92, "fuel_type": "electric",
            "category": "suv", "kwh_per_100km": 17.0
        },
        "Model S": {
            "weight": 2162, "drag_coefficient": 0.208, "frontal_area": 2.34,
            "rolling_resistance": 0.009, "engine_displacement": 0,
            "idle_rate": 0.03, "base_consumption": 0.175, "optimal_speed": 100,
            "accel_cost": 0.025, "efficiency": 0.92, "fuel_type": "electric",
            "category": "sedan", "kwh_per_100km": 17.5
        },
    },
    "Nissan": {
        "Altima": {
            "weight": 1474, "drag_coefficient": 0.26, "frontal_area": 2.22,
            "rolling_resistance": 0.010, "engine_displacement": 2.5,
            "idle_rate": 0.50, "base_consumption": 0.068, "optimal_speed": 80,
            "accel_cost": 0.011, "efficiency": 0.27, "fuel_type": "gasoline",
            "category": "sedan"
        },
        "Rogue": {
            "weight": 1597, "drag_coefficient": 0.33, "frontal_area": 2.66,
            "rolling_resistance": 0.012, "engine_displacement": 2.5,
            "idle_rate": 0.67, "base_consumption": 0.086, "optimal_speed": 75,
            "accel_cost": 0.017, "efficiency": 0.25, "fuel_type": "gasoline",
            "category": "suv"
        },
        "Frontier": {
            "weight": 1835, "drag_coefficient": 0.42, "frontal_area": 3.12,
            "rolling_resistance": 0.013, "engine_displacement": 3.8,
            "idle_rate": 0.90, "base_consumption": 0.115, "optimal_speed": 65,
            "accel_cost": 0.026, "efficiency": 0.22, "fuel_type": "gasoline",
            "category": "truck"
        },
    },
}

# Physical constants
AIR_DENSITY = 1.225  # kg/m³
GRAVITY = 9.81       # m/s²
ENERGY_DENSITY_GASOLINE = 34.2  # MJ/L
ENERGY_DENSITY_DIESEL   = 38.6  # MJ/L
CO2_PER_LITRE_GASOLINE  = 2.31  # kg CO2/L
CO2_PER_KWH             = 0.233 # kg CO2/kWh (grid average)


def get_car_makes():
    return sorted(CAR_DATABASE.keys())


def get_car_models(make):
    return sorted(CAR_DATABASE.get(make, {}).keys())


def get_car_specs(make, model):
    return CAR_DATABASE.get(make, {}).get(model, None)


def decode_polyline(polyline_str):
    index, lat, lng, coordinates = 0, 0, 0, []
    while index < len(polyline_str):
        result, shift = 0, 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat
        result, shift = 0, 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng
        coordinates.append([lat * 1e-5, lng * 1e-5])
    return coordinates


def get_coordinates(place_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_name, "format": "json", "addressdetails": 1, "limit": 5}
    headers = {"User-Agent": "MyRoute/2.0 (abstab@gmail.com)"}
    try:
        r = requests.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"Geocode error: {e}")
    return None


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371 * 2 * math.asin(math.sqrt(a))


# ─────────────────────────────────────────────
# PHYSICS ENGINE
# ─────────────────────────────────────────────

def drag_force(speed_kmh, specs):
    v = speed_kmh / 3.6
    return 0.5 * AIR_DENSITY * specs["drag_coefficient"] * specs["frontal_area"] * v**2


def rolling_force(specs, slope_deg=0):
    return specs["rolling_resistance"] * specs["weight"] * GRAVITY * math.cos(math.radians(slope_deg))


def gravity_force(specs, slope_deg):
    return specs["weight"] * GRAVITY * math.sin(math.radians(slope_deg))


def speed_penalty(speed_kmh, optimal_speed):
    """
    Extra consumption factor vs optimal speed.
    Below optimal → richer mixture / partial throttle losses.
    Above optimal → aerodynamic drag rises sharply.
    """
    ratio = speed_kmh / optimal_speed
    if ratio <= 0:
        return 2.0
    if ratio < 0.5:
        return 1.0 + (0.5 - ratio) * 2.5   # slow city traffic penalty
    if ratio <= 1.0:
        return 1.0 + (1.0 - ratio) * 0.3    # slight penalty below optimal
    # Above optimal: drag grows ∝ v³
    return 1.0 + (ratio - 1.0) ** 2 * 1.8


def calculate_segment_fuel(d_km, t_hr, slope_deg, is_stop_go, specs):
    """
    Physics-based fuel for one route segment.
    Returns litres (or kWh equivalent for EVs treated the same way).
    """
    if t_hr <= 0 or d_km <= 0:
        return 0.0

    avg_speed = d_km / t_hr   # km/h
    fuel_type = specs.get("fuel_type", "gasoline")

    # Idle at very low speed (< 5 km/h)
    if avg_speed < 5:
        idle_t = t_hr * 0.9
        return specs["idle_rate"] * idle_t

    v_ms = avg_speed / 3.6
    d_m  = d_km * 1000

    Fd = drag_force(avg_speed, specs)
    Fr = rolling_force(specs, slope_deg)
    Fg = gravity_force(specs, slope_deg)

    # Net tractive force (uphill = +Fg, downhill regenerates for EVs)
    total_force = Fd + Fr + Fg

    # For downhill, conventional vehicles engine-brake (small -ve fuel save)
    if total_force < 0:
        total_force = max(total_force, -Fr * 0.2)  # tiny save

    work_J = total_force * d_m                      # Joules
    work_MJ = work_J / 1e6

    # Speed penalty factor
    sp = speed_penalty(avg_speed, specs["optimal_speed"])

    if fuel_type == "electric":
        eff = specs["efficiency"]
        energy_kwh = (work_MJ / 3.6) * sp / eff
        # Treat kWh as "litres" for unified math; convert at output
        fuel_eq = energy_kwh / 8.9   # 1 L gasoline ≈ 8.9 kWh thermal; ratio for display
        fuel_l  = energy_kwh / 8.9
    else:
        energy_density = ENERGY_DENSITY_GASOLINE if fuel_type != "diesel" else ENERGY_DENSITY_DIESEL
        fuel_l = work_MJ * sp / (energy_density * specs["efficiency"])

    # Stop-and-go acceleration penalty
    if is_stop_go:
        fuel_l += specs["accel_cost"] * (d_km / 0.5)  # accel events per 500 m

    return max(fuel_l, 0.0)


def simulate_fuel(route_data, specs):
    """
    Full fuel simulation over a decoded ORS route.
    Returns dict with breakdown.
    """
    idle_fuel  = 0.0
    accel_fuel = 0.0
    cruise_fuel= 0.0

    try:
        segments = route_data["segments"][0]["steps"]
    except (KeyError, IndexError):
        return {"idle": 0, "accel": 0, "cruise": 0, "total": 0}

    # Elevation data helps slope calculation
    coords = route_data.get("_coords", [])

    prev_speed = None
    for i, step in enumerate(segments):
        d_km = step.get("distance", 0) / 1000.0
        t_hr = step.get("duration", 0) / 3600.0
        if t_hr <= 0 or d_km <= 0:
            continue

        avg_speed = d_km / t_hr

        # Slope from elevation samples if available
        slope_deg = 0.0
        if i < len(coords) - 1:
            seg_coords = coords[i:i+2]
            if len(seg_coords) == 2 and len(seg_coords[0]) >= 3 and len(seg_coords[1]) >= 3:
                elev_diff = seg_coords[1][2] - seg_coords[0][2]
                horiz_m   = d_km * 1000
                slope_deg = math.degrees(math.atan2(elev_diff, horiz_m)) if horiz_m > 0 else 0

        instruction = step.get("instruction", "").lower()
        stop_keywords = ["turn", "stop", "traffic", "junction", "roundabout", "merge", "exit", "ramp"]
        is_stop_go = any(k in instruction for k in stop_keywords)
        if prev_speed and avg_speed > prev_speed * 1.25:
            is_stop_go = True

        seg_fuel = calculate_segment_fuel(d_km, t_hr, slope_deg, is_stop_go, specs)

        if avg_speed < 5:
            idle_fuel += seg_fuel
        elif is_stop_go:
            # Split: part cruising, part accel
            accel_fuel  += seg_fuel * 0.35
            cruise_fuel += seg_fuel * 0.65
        else:
            cruise_fuel += seg_fuel

        prev_speed = avg_speed

    total = idle_fuel + accel_fuel + cruise_fuel
    return {
        "idle":   round(idle_fuel,  3),
        "accel":  round(accel_fuel, 3),
        "cruise": round(cruise_fuel,3),
        "total":  round(total, 3)
    }


def fuel_to_co2(fuel_l, specs):
    ft = specs.get("fuel_type", "gasoline")
    if ft == "electric":
        # fuel_l here is stored as kWh/8.9 so recover kWh
        kwh = fuel_l * 8.9
        return round(kwh * CO2_PER_KWH, 2)
    return round(fuel_l * CO2_PER_LITRE_GASOLINE, 2)


def fuel_cost_estimate(fuel_l, specs):
    ft = specs.get("fuel_type", "gasoline")
    if ft == "electric":
        kwh = fuel_l * 8.9
        return round(kwh * 0.14, 2)   # $0.14 / kWh average
    return round(fuel_l * 1.45, 2)    # $1.45 / L (~$5.49/gal)


# ─────────────────────────────────────────────
# ROUTE PROCESSING
# ─────────────────────────────────────────────

def process_route(route, start_addr, end_addr, start_coords, end_coords, specs, route_name):
    distance_km  = round(route["summary"]["distance"] / 1000, 2)
    duration_min = round(route["summary"]["duration"] / 60,   2)

    coords = []
    if "geometry" in route:
        if isinstance(route["geometry"], str):
            coords = decode_polyline(route["geometry"])
        elif isinstance(route["geometry"], dict) and "coordinates" in route["geometry"]:
            coords = [[c[1], c[0]] for c in route["geometry"]["coordinates"]]

    route["_coords"] = coords

    steps = []
    if "segments" in route and route["segments"]:
        for seg in route["segments"]:
            for step in seg.get("steps", []):
                if "instruction" in step:
                    steps.append({
                        "instruction": step["instruction"],
                        "distance": round(step.get("distance", 0) / 1000, 2),
                        "duration": round(step.get("duration", 0) / 60,  1)
                    })

    if not steps:
        steps = [
            {"instruction": f"Start at {start_addr}",    "distance": 0,           "duration": 0},
            {"instruction": f"Drive to {end_addr}",      "distance": distance_km, "duration": duration_min},
            {"instruction": "Arrive at destination",     "distance": 0,           "duration": 0},
        ]

    fuel = simulate_fuel(route, specs)
    co2  = fuel_to_co2(fuel["total"], specs)
    cost = fuel_cost_estimate(fuel["total"], specs)

    avg_speed = (distance_km / (duration_min / 60)) if duration_min > 0 else 0
    eff_score = min(100, max(0, round(100 - (fuel["total"] / max(distance_km, 0.1)) * 800, 1)))

    return {
        "name":             route_name,
        "start":            start_addr,
        "end":              end_addr,
        "distance":         distance_km,
        "duration":         duration_min,
        "total_fuel":       fuel["total"],
        "idle_fuel":        fuel["idle"],
        "accel_fuel":       fuel["accel"],
        "cruise_fuel":      fuel["cruise"],
        "fuel_cost":        cost,
        "co2_emissions":    co2,
        "steps":            steps,
        "start_lat":        start_coords[0],
        "start_lng":        start_coords[1],
        "end_lat":          end_coords[0],
        "end_lng":          end_coords[1],
        "route_coordinates":coords,
        "efficiency_score": eff_score,
        "avg_speed":        round(avg_speed, 1),
    }


# ─────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    makes = get_car_makes()
    return render_template("index.html", makes=makes)


@app.route("/api/models")
def api_models():
    make = request.args.get("make", "")
    return jsonify(get_car_models(make))


@app.route("/api/cars")
def api_cars():
    return jsonify(CAR_DATABASE)


@app.route("/api/autocomplete")
def api_autocomplete():
    """Proxy Nominatim autocomplete so we avoid CORS and keep a single User-Agent."""
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([])
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "json",
                "addressdetails": 1,
                "limit": 6,
                "dedupe": 1,
            },
            headers={"User-Agent": "MyRoute/2.0 (abstab@gmail.com)"},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        suggestions = []
        for item in data:
            suggestions.append({
                "display": item.get("display_name", ""),
                "short":   _short_label(item),
                "lat":     float(item["lat"]),
                "lon":     float(item["lon"]),
            })
        return jsonify(suggestions)
    except Exception as e:
        print(f"Autocomplete error: {e}")
        return jsonify([])


def _short_label(item):
    """Build a concise human-readable label from a Nominatim result."""
    addr = item.get("addressdetails", item.get("address", {}))
    parts = []
    for key in ("amenity", "building", "road", "suburb", "city", "town",
                "village", "county", "state", "country"):
        val = addr.get(key)
        if val and val not in parts:
            parts.append(val)
        if len(parts) >= 3:
            break
    return ", ".join(parts) if parts else item.get("display_name", "")[:60]


def _fetch_single_route(coords_payload, preference, headers, ors_url):
    """
    Fetch exactly one ORS route for a given preference.
    Returns the raw route dict or None on failure.
    """
    payload = {
        "coordinates":  coords_payload,
        "preference":   preference,
        "units":        "m",
        "instructions": True,
        "language":     "en",
    }
    try:
        r = requests.post(ors_url, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        routes = r.json().get("routes", [])
        return routes[0] if routes else None
    except Exception as e:
        print(f"ORS single-route error ({preference}): {e}")
        return None


def _fetch_alternative_routes(coords_payload, headers, ors_url):
    """
    Ask ORS for up to 5 diverse alternative routes using recommended preference.
    Uses low share_factor so the alternatives are as different from each other
    as possible, maximising the search space for our energy algorithm.
    Returns a list of raw route dicts (may be empty on failure).
    """
    payload = {
        "coordinates":  coords_payload,
        "preference":   "recommended",
        "units":        "m",
        "instructions": True,
        "language":     "en",
        "alternative_routes": {
            "target_count":  5,     # ask for up to 5 candidates
            "weight_factor": 2.0,   # allow routes up to 2× the optimal weight
            "share_factor":  0.5,   # routes must differ by at least 50%
        },
    }
    try:
        r = requests.post(ors_url, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        return r.json().get("routes", [])
    except Exception as e:
        print(f"ORS alternatives error: {e}")
        return []


def _deduplicate_routes(routes, distance_threshold_km=0.5):
    """
    Remove routes whose distance is within threshold of an already-kept route.
    Works on raw ORS route dicts where distance lives at summary["distance"] in metres.
    Keeps the first occurrence (lowest index = lowest ORS cost).
    """
    kept = []
    seen_distances = []
    for r in routes:
        try:
            d_km = r["summary"]["distance"] / 1000.0
        except (KeyError, TypeError):
            continue
        if all(abs(d_km - s) > distance_threshold_km for s in seen_distances):
            kept.append(r)
            seen_distances.append(d_km)
    return kept


@app.route("/results", methods=["GET"])
def results():
    start_addr = request.args.get("start", "")
    end_addr   = request.args.get("end",   "")
    make       = request.args.get("make",  "")
    model      = request.args.get("model", "")

    if not start_addr or not end_addr:
        return jsonify({"error": "Missing start or end location"}), 400

    specs = get_car_specs(make, model)
    if not specs:
        return jsonify({"error": f"Unknown vehicle: {make} {model}"}), 400

    # Use pre-resolved coords from autocomplete when available
    start_lat = request.args.get("start_lat")
    start_lon = request.args.get("start_lon")
    end_lat   = request.args.get("end_lat")
    end_lon   = request.args.get("end_lon")

    start_coords = (float(start_lat), float(start_lon)) if (start_lat and start_lon) \
                   else get_coordinates(start_addr)
    end_coords   = (float(end_lat),   float(end_lon))   if (end_lat   and end_lon)   \
                   else get_coordinates(end_addr)

    if not start_coords or not end_coords:
        return jsonify({"error": "Could not geocode locations"}), 400

    ors_url = f"{ORS_BASE_URL}/v2/directions/driving-car"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type":  "application/json; charset=utf-8",
        "Accept":        "application/json, application/geo+json",
    }
    coords_payload = [
        [start_coords[1], start_coords[0]],
        [end_coords[1],   end_coords[0]],
    ]

    # ── Step 1: Fetch the definitive Fastest route ────────────────────────────
    # We always display this as-is — it is ORS's own fastest path.
    raw_fastest = _fetch_single_route(coords_payload, "fastest", headers, ors_url)

    # ── Step 2: Gather a wide pool of candidate routes for eco scoring ────────
    # Start with up to 5 diverse alternatives from ORS, then also add the
    # "shortest" preference route which often takes quieter, lower-speed roads
    # that the energy model rewards for reduced drag.
    candidate_raws = _fetch_alternative_routes(coords_payload, headers, ors_url)

    raw_shortest = _fetch_single_route(coords_payload, "shortest", headers, ors_url)
    if raw_shortest:
        candidate_raws.append(raw_shortest)

    # Also include the fastest route itself in the candidate pool — it might
    # actually be the most eco too (e.g. a fast motorway with no stops).
    if raw_fastest:
        candidate_raws.append(raw_fastest)

    # Fall back if everything failed
    if not candidate_raws and not raw_fastest:
        mock = _mock_route(start_addr, end_addr, start_coords, end_coords, specs)
        mock["tag"] = "eco"
        fastest_mock = mock.copy()
        fastest_mock["tag"] = "fastest"
        fastest_mock["name"] = "Fastest Route"
        comparison = [
            {"name": mock["name"], "tag": "eco", "distance": mock["distance"],
             "duration": mock["duration"], "total_fuel": mock["total_fuel"],
             "co2": mock["co2_emissions"], "cost": mock["fuel_cost"],
             "eff_score": mock["efficiency_score"]},
            {"name": fastest_mock["name"], "tag": "fastest", "distance": fastest_mock["distance"],
             "duration": fastest_mock["duration"], "total_fuel": fastest_mock["total_fuel"],
             "co2": fastest_mock["co2_emissions"], "cost": fastest_mock["fuel_cost"],
             "eff_score": fastest_mock["efficiency_score"]},
        ]
        return render_template("results.html",
            start=start_addr, end=end_addr, make=make, model=model,
            fuel_type=specs.get("fuel_type","gasoline"), specs=specs,
            eco=mock, fastest=fastest_mock, comparison=comparison,
            candidates_evaluated=1, active_tag="eco")

    # ── Step 3: Score every candidate through the physics energy model ────────
    # Deduplicate first so we don't waste cycles on near-identical routes.
    unique_candidates = _deduplicate_routes(candidate_raws)

    scored_candidates = []
    for i, raw in enumerate(unique_candidates):
        label = f"Candidate {i + 1}"
        processed = process_route(raw, start_addr, end_addr,
                                  start_coords, end_coords, specs, label)
        scored_candidates.append(processed)

    # The eco route is whichever candidate our physics model rates lowest fuel
    eco_route = min(scored_candidates, key=lambda x: x["total_fuel"])
    eco_route["tag"]  = "eco"
    eco_route["name"] = "Eco Route"

    # ── Step 4: Process the dedicated Fastest route ───────────────────────────
    if raw_fastest:
        fastest_route = process_route(raw_fastest, start_addr, end_addr,
                                      start_coords, end_coords, specs, "Fastest Route")
    else:
        # Rare fallback: use the fastest among candidates
        fastest_route = min(scored_candidates, key=lambda x: x["duration"]).copy()
        fastest_route["name"] = "Fastest Route"

    fastest_route["tag"] = "fastest"

    # ── Step 5: Build comparison table ───────────────────────────────────────
    def row(r):
        return {
            "name":       r["name"],
            "tag":        r["tag"],
            "distance":   r["distance"],
            "duration":   r["duration"],
            "total_fuel": r["total_fuel"],
            "co2":        r["co2_emissions"],
            "cost":       r["fuel_cost"],
            "eff_score":  r["efficiency_score"],
        }

    comparison = [row(eco_route), row(fastest_route)]
    fuel_type  = specs.get("fuel_type", "gasoline")
    candidates_evaluated = len(scored_candidates)

    return render_template(
        "results.html",
        start               = start_addr,
        end                 = end_addr,
        make                = make,
        model               = model,
        fuel_type           = fuel_type,
        specs               = specs,
        eco                 = eco_route,
        fastest             = fastest_route,
        comparison          = comparison,
        candidates_evaluated= candidates_evaluated,
        active_tag          = "eco",
    )


def _mock_route(start_addr, end_addr, start_coords, end_coords, specs):
    dist = haversine_km(start_coords[0], start_coords[1], end_coords[0], end_coords[1])
    dur  = dist * 60 / 60
    pts  = [[start_coords[0] + i/10*(end_coords[0]-start_coords[0]),
             start_coords[1] + i/10*(end_coords[1]-start_coords[1])] for i in range(11)]
    fuel_total = dist * specs["base_consumption"]
    return {
        "name": "Estimated Route", "tag": "eco",
        "start": start_addr, "end": end_addr,
        "distance": round(dist, 2), "duration": round(dur, 2),
        "total_fuel": round(fuel_total, 3),
        "idle_fuel": round(fuel_total*0.1, 3),
        "accel_fuel": round(fuel_total*0.25, 3),
        "cruise_fuel": round(fuel_total*0.65, 3),
        "fuel_cost": fuel_cost_estimate(fuel_total, specs),
        "co2_emissions": fuel_to_co2(fuel_total, specs),
        "steps": [
            {"instruction": f"Start at {start_addr}", "distance": 0, "duration": 0},
            {"instruction": f"Drive to {end_addr}",   "distance": round(dist,2), "duration": round(dur,1)},
            {"instruction": "Arrive at destination",  "distance": 0, "duration": 0},
        ],
        "start_lat": start_coords[0], "start_lng": start_coords[1],
        "end_lat":   end_coords[0],   "end_lng":   end_coords[1],
        "route_coordinates": pts,
        "efficiency_score": 70,
        "avg_speed": 60.0,
    }


if __name__ == "__main__":
    app.run(debug=True)