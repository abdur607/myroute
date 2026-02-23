from flask import Flask, render_template, request, jsonify
import requests
import math
import concurrent.futures

app = Flask(__name__)

ORS_BASE_URL = "https://api.openrouteservice.org"

# ─── Physical constants ───────────────────────────────────────────────────────
AIR_DENSITY_STD         = 1.225
GRAVITY                 = 9.81
ENERGY_DENSITY_GASOLINE = 34.2
ENERGY_DENSITY_DIESEL   = 38.6
CO2_GASOLINE            = 2.31
CO2_DIESEL              = 2.68
CO2_PER_KWH             = 0.233
PRICE_GASOLINE          = 1.00
PRICE_DIESEL            = 1.08
PRICE_ELECTRICITY       = 0.16

CLASS_AVG_L100KM = {
    "sedan": 8.5, "suv": 11.0, "truck": 13.5,
    "hybrid": 5.0, "electric": 2.2,
}

ROAD_CLASS_SPEED = {
    "motorway": 110, "motorway_link": 80,
    "trunk": 90,     "trunk_link": 70,
    "primary": 70,   "primary_link": 55,
    "secondary": 60, "secondary_link": 50,
    "tertiary": 50,  "tertiary_link": 40,
    "residential": 30, "living_street": 15,
    "unclassified": 50, "service": 20,
}

SURFACE_RR = {
    "paved": 1.00, "asphalt": 1.00, "concrete": 1.02,
    "compacted": 1.10, "fine_gravel": 1.20, "gravel": 1.35,
    "unpaved": 1.40, "dirt": 1.45, "cobblestone": 1.55,
    "sett": 1.50, "grass": 1.65,
}

STYLE_FACTORS = {"calm": 0.85, "normal": 1.00, "aggressive": 1.22}

# ─── Car database ─────────────────────────────────────────────────────────────
CAR_DATABASE = {
    "Toyota": {
        "Camry":      {"weight":1560,"drag_coefficient":0.28,"frontal_area":2.24,"rolling_resistance":0.010,"engine_displacement":2.5,"idle_rate":0.55,"base_consumption":0.072,"optimal_speed":80,"accel_cost":0.012,"efficiency":0.26,"fuel_type":"gasoline","category":"sedan","cold_start_ml":18,"regen_fraction":0.00,"hvac_lph":0.80,"city_l100km":10.2,"hwy_l100km":6.7},
        "Corolla":    {"weight":1355,"drag_coefficient":0.27,"frontal_area":2.19,"rolling_resistance":0.010,"engine_displacement":2.0,"idle_rate":0.48,"base_consumption":0.064,"optimal_speed":80,"accel_cost":0.010,"efficiency":0.27,"fuel_type":"gasoline","category":"sedan","cold_start_ml":15,"regen_fraction":0.00,"hvac_lph":0.70,"city_l100km":9.4,"hwy_l100km":6.5},
        "RAV4":       {"weight":1735,"drag_coefficient":0.33,"frontal_area":2.65,"rolling_resistance":0.012,"engine_displacement":2.5,"idle_rate":0.72,"base_consumption":0.085,"optimal_speed":75,"accel_cost":0.018,"efficiency":0.25,"fuel_type":"gasoline","category":"suv","cold_start_ml":22,"regen_fraction":0.00,"hvac_lph":1.00,"city_l100km":11.8,"hwy_l100km":8.7},
        "Prius":      {"weight":1420,"drag_coefficient":0.24,"frontal_area":2.16,"rolling_resistance":0.009,"engine_displacement":1.8,"idle_rate":0.10,"base_consumption":0.042,"optimal_speed":85,"accel_cost":0.006,"efficiency":0.38,"fuel_type":"hybrid","category":"hybrid","cold_start_ml":6,"regen_fraction":0.30,"hvac_lph":0.40,"city_l100km":4.7,"hwy_l100km":5.3},
        "Highlander": {"weight":2041,"drag_coefficient":0.35,"frontal_area":2.90,"rolling_resistance":0.013,"engine_displacement":3.5,"idle_rate":0.95,"base_consumption":0.105,"optimal_speed":70,"accel_cost":0.022,"efficiency":0.23,"fuel_type":"gasoline","category":"suv","cold_start_ml":28,"regen_fraction":0.00,"hvac_lph":1.20,"city_l100km":13.8,"hwy_l100km":10.2},
        "Tacoma":     {"weight":1895,"drag_coefficient":0.40,"frontal_area":3.10,"rolling_resistance":0.013,"engine_displacement":3.5,"idle_rate":0.90,"base_consumption":0.110,"optimal_speed":65,"accel_cost":0.025,"efficiency":0.22,"fuel_type":"gasoline","category":"truck","cold_start_ml":30,"regen_fraction":0.00,"hvac_lph":1.10,"city_l100km":14.7,"hwy_l100km":11.8},
    },
    "Honda": {
        "Civic":     {"weight":1278,"drag_coefficient":0.28,"frontal_area":2.19,"rolling_resistance":0.010,"engine_displacement":1.5,"idle_rate":0.45,"base_consumption":0.060,"optimal_speed":80,"accel_cost":0.009,"efficiency":0.28,"fuel_type":"gasoline","category":"sedan","cold_start_ml":14,"regen_fraction":0.00,"hvac_lph":0.65,"city_l100km":8.9,"hwy_l100km":6.4},
        "Accord":    {"weight":1498,"drag_coefficient":0.27,"frontal_area":2.26,"rolling_resistance":0.010,"engine_displacement":1.5,"idle_rate":0.52,"base_consumption":0.068,"optimal_speed":80,"accel_cost":0.011,"efficiency":0.27,"fuel_type":"gasoline","category":"sedan","cold_start_ml":17,"regen_fraction":0.00,"hvac_lph":0.75,"city_l100km":9.8,"hwy_l100km":7.1},
        "CR-V":      {"weight":1590,"drag_coefficient":0.33,"frontal_area":2.68,"rolling_resistance":0.012,"engine_displacement":1.5,"idle_rate":0.65,"base_consumption":0.082,"optimal_speed":75,"accel_cost":0.016,"efficiency":0.26,"fuel_type":"gasoline","category":"suv","cold_start_ml":20,"regen_fraction":0.00,"hvac_lph":0.95,"city_l100km":11.2,"hwy_l100km":8.4},
        "Pilot":     {"weight":2005,"drag_coefficient":0.36,"frontal_area":2.88,"rolling_resistance":0.013,"engine_displacement":3.5,"idle_rate":0.92,"base_consumption":0.108,"optimal_speed":70,"accel_cost":0.021,"efficiency":0.23,"fuel_type":"gasoline","category":"suv","cold_start_ml":27,"regen_fraction":0.00,"hvac_lph":1.15,"city_l100km":14.1,"hwy_l100km":10.7},
        "Ridgeline": {"weight":1997,"drag_coefficient":0.39,"frontal_area":3.05,"rolling_resistance":0.013,"engine_displacement":3.5,"idle_rate":0.88,"base_consumption":0.108,"optimal_speed":65,"accel_cost":0.024,"efficiency":0.22,"fuel_type":"gasoline","category":"truck","cold_start_ml":28,"regen_fraction":0.00,"hvac_lph":1.10,"city_l100km":14.7,"hwy_l100km":11.2},
    },
    "Ford": {
        "F-150":   {"weight":2065,"drag_coefficient":0.41,"frontal_area":3.32,"rolling_resistance":0.013,"engine_displacement":3.5,"idle_rate":1.00,"base_consumption":0.120,"optimal_speed":65,"accel_cost":0.028,"efficiency":0.21,"fuel_type":"gasoline","category":"truck","cold_start_ml":35,"regen_fraction":0.00,"hvac_lph":1.30,"city_l100km":16.3,"hwy_l100km":12.4},
        "Mustang": {"weight":1696,"drag_coefficient":0.35,"frontal_area":2.32,"rolling_resistance":0.011,"engine_displacement":5.0,"idle_rate":0.80,"base_consumption":0.105,"optimal_speed":90,"accel_cost":0.022,"efficiency":0.22,"fuel_type":"gasoline","category":"sedan","cold_start_ml":24,"regen_fraction":0.00,"hvac_lph":0.90,"city_l100km":15.1,"hwy_l100km":10.7},
        "Explorer":{"weight":2021,"drag_coefficient":0.38,"frontal_area":2.92,"rolling_resistance":0.013,"engine_displacement":2.3,"idle_rate":0.88,"base_consumption":0.105,"optimal_speed":70,"accel_cost":0.022,"efficiency":0.23,"fuel_type":"gasoline","category":"suv","cold_start_ml":26,"regen_fraction":0.00,"hvac_lph":1.10,"city_l100km":13.8,"hwy_l100km":10.2},
        "Escape":  {"weight":1607,"drag_coefficient":0.34,"frontal_area":2.65,"rolling_resistance":0.012,"engine_displacement":1.5,"idle_rate":0.65,"base_consumption":0.083,"optimal_speed":75,"accel_cost":0.016,"efficiency":0.25,"fuel_type":"gasoline","category":"suv","cold_start_ml":19,"regen_fraction":0.00,"hvac_lph":0.90,"city_l100km":11.8,"hwy_l100km":8.7},
        "Bronco":  {"weight":1975,"drag_coefficient":0.45,"frontal_area":3.15,"rolling_resistance":0.014,"engine_displacement":2.3,"idle_rate":0.92,"base_consumption":0.115,"optimal_speed":65,"accel_cost":0.026,"efficiency":0.21,"fuel_type":"gasoline","category":"truck","cold_start_ml":30,"regen_fraction":0.00,"hvac_lph":1.15,"city_l100km":16.8,"hwy_l100km":13.1},
    },
    "BMW": {
        "3 Series": {"weight":1540,"drag_coefficient":0.26,"frontal_area":2.22,"rolling_resistance":0.010,"engine_displacement":2.0,"idle_rate":0.55,"base_consumption":0.072,"optimal_speed":85,"accel_cost":0.013,"efficiency":0.26,"fuel_type":"gasoline","category":"sedan","cold_start_ml":17,"regen_fraction":0.00,"hvac_lph":0.80,"city_l100km":10.7,"hwy_l100km":7.1},
        "5 Series": {"weight":1795,"drag_coefficient":0.25,"frontal_area":2.31,"rolling_resistance":0.010,"engine_displacement":2.0,"idle_rate":0.60,"base_consumption":0.082,"optimal_speed":85,"accel_cost":0.015,"efficiency":0.26,"fuel_type":"gasoline","category":"sedan","cold_start_ml":20,"regen_fraction":0.00,"hvac_lph":0.85,"city_l100km":11.8,"hwy_l100km":7.8},
        "X5":       {"weight":2175,"drag_coefficient":0.33,"frontal_area":2.85,"rolling_resistance":0.012,"engine_displacement":3.0,"idle_rate":0.95,"base_consumption":0.110,"optimal_speed":75,"accel_cost":0.023,"efficiency":0.24,"fuel_type":"gasoline","category":"suv","cold_start_ml":29,"regen_fraction":0.00,"hvac_lph":1.20,"city_l100km":14.7,"hwy_l100km":10.7},
        "X3":       {"weight":1845,"drag_coefficient":0.31,"frontal_area":2.66,"rolling_resistance":0.012,"engine_displacement":2.0,"idle_rate":0.78,"base_consumption":0.092,"optimal_speed":75,"accel_cost":0.019,"efficiency":0.25,"fuel_type":"gasoline","category":"suv","cold_start_ml":23,"regen_fraction":0.00,"hvac_lph":1.05,"city_l100km":13.1,"hwy_l100km":9.4},
    },
    "Mercedes-Benz": {
        "C-Class": {"weight":1605,"drag_coefficient":0.24,"frontal_area":2.21,"rolling_resistance":0.010,"engine_displacement":2.0,"idle_rate":0.58,"base_consumption":0.075,"optimal_speed":85,"accel_cost":0.013,"efficiency":0.26,"fuel_type":"gasoline","category":"sedan","cold_start_ml":18,"regen_fraction":0.00,"hvac_lph":0.80,"city_l100km":11.2,"hwy_l100km":7.5},
        "E-Class": {"weight":1905,"drag_coefficient":0.23,"frontal_area":2.28,"rolling_resistance":0.010,"engine_displacement":2.0,"idle_rate":0.65,"base_consumption":0.088,"optimal_speed":85,"accel_cost":0.016,"efficiency":0.26,"fuel_type":"gasoline","category":"sedan","cold_start_ml":22,"regen_fraction":0.00,"hvac_lph":0.90,"city_l100km":12.4,"hwy_l100km":8.1},
        "GLE":     {"weight":2215,"drag_coefficient":0.34,"frontal_area":2.88,"rolling_resistance":0.012,"engine_displacement":3.0,"idle_rate":1.00,"base_consumption":0.115,"optimal_speed":75,"accel_cost":0.024,"efficiency":0.23,"fuel_type":"gasoline","category":"suv","cold_start_ml":30,"regen_fraction":0.00,"hvac_lph":1.25,"city_l100km":15.7,"hwy_l100km":11.2},
    },
    "Volkswagen": {
        "Golf":   {"weight":1317,"drag_coefficient":0.29,"frontal_area":2.20,"rolling_resistance":0.010,"engine_displacement":1.4,"idle_rate":0.45,"base_consumption":0.062,"optimal_speed":80,"accel_cost":0.010,"efficiency":0.27,"fuel_type":"gasoline","category":"sedan","cold_start_ml":13,"regen_fraction":0.00,"hvac_lph":0.65,"city_l100km":9.4,"hwy_l100km":6.5},
        "Tiguan": {"weight":1655,"drag_coefficient":0.33,"frontal_area":2.66,"rolling_resistance":0.012,"engine_displacement":2.0,"idle_rate":0.68,"base_consumption":0.086,"optimal_speed":75,"accel_cost":0.017,"efficiency":0.25,"fuel_type":"gasoline","category":"suv","cold_start_ml":21,"regen_fraction":0.00,"hvac_lph":1.00,"city_l100km":12.4,"hwy_l100km":9.1},
        "Passat": {"weight":1492,"drag_coefficient":0.25,"frontal_area":2.27,"rolling_resistance":0.010,"engine_displacement":2.0,"idle_rate":0.52,"base_consumption":0.070,"optimal_speed":82,"accel_cost":0.012,"efficiency":0.27,"fuel_type":"gasoline","category":"sedan","cold_start_ml":16,"regen_fraction":0.00,"hvac_lph":0.75,"city_l100km":10.2,"hwy_l100km":7.1},
    },
    "Chevrolet": {
        "Silverado": {"weight":2136,"drag_coefficient":0.42,"frontal_area":3.38,"rolling_resistance":0.013,"engine_displacement":5.3,"idle_rate":1.05,"base_consumption":0.125,"optimal_speed":65,"accel_cost":0.030,"efficiency":0.21,"fuel_type":"gasoline","category":"truck","cold_start_ml":38,"regen_fraction":0.00,"hvac_lph":1.35,"city_l100km":17.8,"hwy_l100km":13.1},
        "Equinox":   {"weight":1614,"drag_coefficient":0.33,"frontal_area":2.66,"rolling_resistance":0.012,"engine_displacement":1.5,"idle_rate":0.65,"base_consumption":0.083,"optimal_speed":75,"accel_cost":0.016,"efficiency":0.25,"fuel_type":"gasoline","category":"suv","cold_start_ml":19,"regen_fraction":0.00,"hvac_lph":0.95,"city_l100km":11.8,"hwy_l100km":9.1},
        "Tahoe":     {"weight":2518,"drag_coefficient":0.40,"frontal_area":3.20,"rolling_resistance":0.014,"engine_displacement":5.3,"idle_rate":1.20,"base_consumption":0.145,"optimal_speed":65,"accel_cost":0.035,"efficiency":0.20,"fuel_type":"gasoline","category":"suv","cold_start_ml":42,"regen_fraction":0.00,"hvac_lph":1.50,"city_l100km":18.8,"hwy_l100km":13.8},
        "Malibu":    {"weight":1470,"drag_coefficient":0.29,"frontal_area":2.22,"rolling_resistance":0.010,"engine_displacement":1.5,"idle_rate":0.50,"base_consumption":0.068,"optimal_speed":80,"accel_cost":0.011,"efficiency":0.27,"fuel_type":"gasoline","category":"sedan","cold_start_ml":16,"regen_fraction":0.00,"hvac_lph":0.70,"city_l100km":10.2,"hwy_l100km":7.1},
    },
    "Subaru": {
        "Outback":  {"weight":1657,"drag_coefficient":0.33,"frontal_area":2.60,"rolling_resistance":0.011,"engine_displacement":2.5,"idle_rate":0.68,"base_consumption":0.087,"optimal_speed":75,"accel_cost":0.017,"efficiency":0.25,"fuel_type":"gasoline","category":"suv","cold_start_ml":21,"regen_fraction":0.00,"hvac_lph":1.00,"city_l100km":12.4,"hwy_l100km":9.4},
        "Forester": {"weight":1590,"drag_coefficient":0.34,"frontal_area":2.64,"rolling_resistance":0.012,"engine_displacement":2.5,"idle_rate":0.65,"base_consumption":0.085,"optimal_speed":75,"accel_cost":0.017,"efficiency":0.25,"fuel_type":"gasoline","category":"suv","cold_start_ml":20,"regen_fraction":0.00,"hvac_lph":0.95,"city_l100km":12.1,"hwy_l100km":9.1},
        "Impreza":  {"weight":1349,"drag_coefficient":0.30,"frontal_area":2.20,"rolling_resistance":0.010,"engine_displacement":2.0,"idle_rate":0.48,"base_consumption":0.068,"optimal_speed":78,"accel_cost":0.011,"efficiency":0.26,"fuel_type":"gasoline","category":"sedan","cold_start_ml":15,"regen_fraction":0.00,"hvac_lph":0.70,"city_l100km":10.2,"hwy_l100km":7.8},
    },
    "Hyundai": {
        "Elantra": {"weight":1322,"drag_coefficient":0.27,"frontal_area":2.18,"rolling_resistance":0.010,"engine_displacement":2.0,"idle_rate":0.46,"base_consumption":0.063,"optimal_speed":80,"accel_cost":0.010,"efficiency":0.27,"fuel_type":"gasoline","category":"sedan","cold_start_ml":14,"regen_fraction":0.00,"hvac_lph":0.65,"city_l100km":9.4,"hwy_l100km":6.7},
        "Tucson":  {"weight":1615,"drag_coefficient":0.33,"frontal_area":2.65,"rolling_resistance":0.012,"engine_displacement":2.5,"idle_rate":0.67,"base_consumption":0.085,"optimal_speed":75,"accel_cost":0.017,"efficiency":0.25,"fuel_type":"gasoline","category":"suv","cold_start_ml":20,"regen_fraction":0.00,"hvac_lph":1.00,"city_l100km":12.1,"hwy_l100km":9.1},
        "Sonata":  {"weight":1495,"drag_coefficient":0.25,"frontal_area":2.23,"rolling_resistance":0.010,"engine_displacement":2.5,"idle_rate":0.52,"base_consumption":0.070,"optimal_speed":82,"accel_cost":0.012,"efficiency":0.27,"fuel_type":"gasoline","category":"sedan","cold_start_ml":16,"regen_fraction":0.00,"hvac_lph":0.75,"city_l100km":10.2,"hwy_l100km":7.1},
    },
    "Kia": {
        "Sportage": {"weight":1576,"drag_coefficient":0.33,"frontal_area":2.64,"rolling_resistance":0.012,"engine_displacement":2.5,"idle_rate":0.66,"base_consumption":0.084,"optimal_speed":75,"accel_cost":0.016,"efficiency":0.25,"fuel_type":"gasoline","category":"suv","cold_start_ml":19,"regen_fraction":0.00,"hvac_lph":0.95,"city_l100km":11.8,"hwy_l100km":8.7},
        "Sorento":  {"weight":1835,"drag_coefficient":0.34,"frontal_area":2.78,"rolling_resistance":0.012,"engine_displacement":2.5,"idle_rate":0.78,"base_consumption":0.095,"optimal_speed":72,"accel_cost":0.020,"efficiency":0.24,"fuel_type":"gasoline","category":"suv","cold_start_ml":24,"regen_fraction":0.00,"hvac_lph":1.10,"city_l100km":13.1,"hwy_l100km":9.8},
        "K5":       {"weight":1477,"drag_coefficient":0.27,"frontal_area":2.20,"rolling_resistance":0.010,"engine_displacement":2.5,"idle_rate":0.51,"base_consumption":0.070,"optimal_speed":82,"accel_cost":0.012,"efficiency":0.27,"fuel_type":"gasoline","category":"sedan","cold_start_ml":16,"regen_fraction":0.00,"hvac_lph":0.75,"city_l100km":10.2,"hwy_l100km":7.1},
    },
    "Tesla": {
        "Model 3": {"weight":1611,"drag_coefficient":0.23,"frontal_area":2.22,"rolling_resistance":0.009,"engine_displacement":0,"idle_rate":0.02,"base_consumption":0.155,"optimal_speed":90,"accel_cost":0.015,"efficiency":0.92,"fuel_type":"electric","category":"sedan","cold_start_ml":0,"regen_fraction":0.70,"hvac_lph":0.00,"city_l100km":6.7,"hwy_l100km":7.4,"kwh_per_100km":14.9},
        "Model Y": {"weight":1979,"drag_coefficient":0.23,"frontal_area":2.66,"rolling_resistance":0.009,"engine_displacement":0,"idle_rate":0.03,"base_consumption":0.170,"optimal_speed":90,"accel_cost":0.018,"efficiency":0.92,"fuel_type":"electric","category":"suv","cold_start_ml":0,"regen_fraction":0.70,"hvac_lph":0.00,"city_l100km":7.4,"hwy_l100km":8.1,"kwh_per_100km":16.9},
        "Model S": {"weight":2162,"drag_coefficient":0.208,"frontal_area":2.34,"rolling_resistance":0.009,"engine_displacement":0,"idle_rate":0.03,"base_consumption":0.175,"optimal_speed":100,"accel_cost":0.020,"efficiency":0.92,"fuel_type":"electric","category":"sedan","cold_start_ml":0,"regen_fraction":0.72,"hvac_lph":0.00,"city_l100km":7.8,"hwy_l100km":8.5,"kwh_per_100km":18.6},
    },
    "Nissan": {
        "Altima":   {"weight":1474,"drag_coefficient":0.26,"frontal_area":2.22,"rolling_resistance":0.010,"engine_displacement":2.5,"idle_rate":0.50,"base_consumption":0.068,"optimal_speed":80,"accel_cost":0.011,"efficiency":0.27,"fuel_type":"gasoline","category":"sedan","cold_start_ml":16,"regen_fraction":0.00,"hvac_lph":0.75,"city_l100km":10.2,"hwy_l100km":7.1},
        "Rogue":    {"weight":1597,"drag_coefficient":0.33,"frontal_area":2.66,"rolling_resistance":0.012,"engine_displacement":2.5,"idle_rate":0.67,"base_consumption":0.086,"optimal_speed":75,"accel_cost":0.017,"efficiency":0.25,"fuel_type":"gasoline","category":"suv","cold_start_ml":20,"regen_fraction":0.00,"hvac_lph":0.95,"city_l100km":12.1,"hwy_l100km":9.1},
        "Frontier": {"weight":1835,"drag_coefficient":0.42,"frontal_area":3.12,"rolling_resistance":0.013,"engine_displacement":3.8,"idle_rate":0.90,"base_consumption":0.115,"optimal_speed":65,"accel_cost":0.026,"efficiency":0.22,"fuel_type":"gasoline","category":"truck","cold_start_ml":30,"regen_fraction":0.00,"hvac_lph":1.10,"city_l100km":15.7,"hwy_l100km":12.4},
    },
}

# ─── Utilities ────────────────────────────────────────────────────────────────
def get_car_makes():   return sorted(CAR_DATABASE.keys())
def get_car_models(m): return sorted(CAR_DATABASE.get(m, {}).keys())
def get_car_specs(make, model): return CAR_DATABASE.get(make, {}).get(model)

def haversine_km(lat1, lon1, lat2, lon2):
    lat1,lon1,lat2,lon2 = map(math.radians,[lat1,lon1,lat2,lon2])
    dlat,dlon = lat2-lat1, lon2-lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371*2*math.asin(math.sqrt(a))

def bearing_deg(lat1,lon1,lat2,lon2):
    lat1,lon1,lat2,lon2 = map(math.radians,[lat1,lon1,lat2,lon2])
    x = math.sin(lon2-lon1)*math.cos(lat2)
    y = math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(lon2-lon1)
    return (math.degrees(math.atan2(x,y))+360)%360

def decode_polyline(poly):
    index=lat=lng=0; coords=[]
    while index<len(poly):
        result=shift=0
        while True:
            b=ord(poly[index])-63; index+=1
            result|=(b&0x1f)<<shift; shift+=5
            if b<0x20: break
        lat+=(~(result>>1) if result&1 else result>>1)
        result=shift=0
        while True:
            b=ord(poly[index])-63; index+=1
            result|=(b&0x1f)<<shift; shift+=5
            if b<0x20: break
        lng+=(~(result>>1) if result&1 else result>>1)
        coords.append([lat*1e-5,lng*1e-5])
    return coords

def get_coordinates(place):
    try:
        r=requests.get("https://nominatim.openstreetmap.org/search",
            params={"q":place,"format":"json","limit":1},
            headers={"User-Agent":"MyRoute/2.0"},timeout=8)
        d=r.json()
        if d: return float(d[0]["lat"]),float(d[0]["lon"])
    except: pass
    return None

# ─── Weather (Open-Meteo, free, no key) ──────────────────────────────────────
def fetch_weather(lat, lon):
    try:
        r=requests.get("https://api.open-meteo.com/v1/forecast",params={
            "latitude":lat,"longitude":lon,
            "current":"temperature_2m,wind_speed_10m,wind_direction_10m,precipitation",
            "wind_speed_unit":"kmh","forecast_days":1},timeout=8)
        r.raise_for_status()
        c=r.json().get("current",{})
        return {"temperature_c":float(c.get("temperature_2m",15)),
                "wind_speed_kmh":float(c.get("wind_speed_10m",0)),
                "wind_direction_deg":float(c.get("wind_direction_10m",0)),
                "precipitation_mm":float(c.get("precipitation",0))}
    except Exception as e:
        print(f"Weather error: {e}"); return None

# ─── ORS helpers ─────────────────────────────────────────────────────────────
def _ors_headers():
    return {"Authorization":ORS_API_KEY,
            "Content-Type":"application/json; charset=utf-8",
            "Accept":"application/json"}

def _ors_post(payload):
    """Make one ORS directions call. Returns list of route dicts (may be empty)."""
    url = f"{ORS_BASE_URL}/v2/directions/driving-car"
    try:
        r=requests.post(url,json=payload,headers=_ors_headers(),timeout=30)
        if not r.ok:
            print(f"ORS {r.status_code}: {r.text[:200]}")
            return []
        return r.json().get("routes",[])
    except Exception as e:
        print(f"ORS error: {e}"); return []

def _base(coords, preference="recommended", avoid=None, with_alts=False):
    """Build an ORS payload. Optionally request up to 3 alternatives."""
    p={"coordinates":coords,"preference":preference,
       "units":"m","instructions":True,"language":"en"}
    if avoid:
        p["options"]={"avoid_features":avoid}
    if with_alts:
        # ORS public API hard cap: target_count must be ≤ 3
        p["alternative_routes"]={"target_count":3,"weight_factor":2.0,"share_factor":0.3}
    return p

def _generate_via_points(start_coords, end_coords, n_along=4, n_perp=3):
    """
    Generate a grid of via-points spread laterally across the A→B corridor.
    Each via-point forces ORS to route through a different part of the road
    network, guaranteeing genuine path diversity beyond what alternatives provides.
    Returns list of [lon, lat] points for ORS payloads.
    """
    lat1,lon1 = start_coords; lat2,lon2 = end_coords
    dlat=lat2-lat1; dlon=lon2-lon1
    mag=math.sqrt(dlat**2+dlon**2)
    if mag==0: return []
    # Unit perpendicular (rotate 90°)
    plat=-dlon/mag; plon=dlat/mag
    spread=mag*0.35   # spread ±35% of route length either side
    pts=[]
    for i in range(n_along):
        frac=(i+1)/(n_along+1)
        blat=lat1+frac*dlat; blon=lon1+frac*dlon
        for j in range(n_perp):
            off=(j/(n_perp-1)-0.5)*2*spread if n_perp>1 else 0
            pts.append([blon+off*plon, blat+off*plat])  # [lon,lat] for ORS
    return pts

# ─── Route deduplication by geometry fingerprint ─────────────────────────────
def _fingerprint(route):
    """Sample route at 25/50/75% to produce a geometry-based identity key."""
    geom=route.get("geometry","")
    coords=decode_polyline(geom) if isinstance(geom,str) and geom else []
    if len(coords)<4:
        d=route.get("summary",{}).get("distance",0)
        return (round(d,-2),)
    n=len(coords)
    return tuple((round(coords[k][0],3),round(coords[k][1],3))
                 for k in [n//4,n//2,3*n//4])

def _dedupe(routes):
    kept,seen=[],set()
    for r in routes:
        try: fp=_fingerprint(r)
        except: continue
        if fp not in seen:
            kept.append(r); seen.add(fp)
    return kept

# ─── Physics engine ───────────────────────────────────────────────────────────
def air_density(t): return AIR_DENSITY_STD*(288.15/(t+273.15))

def epa_calibration_factor(specs):
    """
    Compute a per-vehicle calibration factor so the physics model output
    matches EPA combined fuel economy figures.

    The simplified physics (drag + rolling resistance) systematically
    underestimates real fuel consumption by 2-3x because it omits:
      - Engine part-load thermal inefficiency
      - Drivetrain friction and pumping losses
      - Alternator / auxiliary loads
      - Fuel enrichment during transients

    Dividing EPA_combined by model_at_combined_speed gives a multiplier
    that anchors absolute fuel values to real-world EPA figures while
    preserving relative differences between routes (which drives eco scoring).
    """
    ft  = specs.get('fuel_type', 'gasoline')
    w   = specs['weight']
    cd  = specs['drag_coefficient']
    A   = specs['frontal_area']
    crr = specs['rolling_resistance']
    eff = specs['efficiency']
    city = specs.get('city_l100km', 10.0)
    hwy  = specs.get('hwy_l100km',  7.0)
    epa_combined = (city + hwy) / 2.0

    v   = 60.0 / 3.6          # combined-cycle proxy speed (60 km/h)
    rho = air_density(15.0)   # standard conditions
    Fd  = 0.5 * rho * cd * A * v**2
    Fr  = crr * w * GRAVITY
    Fn  = Fd + Fr
    work_MJ = Fn * 1000.0 / 1e6   # MJ per km

    if ft == 'electric':
        ed = 3.6 * eff         # effective MJ/L-equivalent
    elif ft == 'diesel':
        ed = ENERGY_DENSITY_DIESEL * eff
    else:
        ed = ENERGY_DENSITY_GASOLINE * eff

    model_l100 = work_MJ / ed * 100.0
    return epa_combined / max(model_l100, 0.01)

def _road_class(step):
    name=(step.get("name") or "").lower()
    instr=(step.get("instruction") or "").lower()
    for k in ["motorway","highway","interstate","freeway","autobahn"]:
        if k in name: return "motorway"
    for k in ["trunk","a-road"]:
        if k in name: return "trunk"
    if "primary" in name: return "primary"
    if "secondary" in name: return "secondary"
    if "roundabout" in instr: return "secondary"
    for k in ["residential","close","grove"]:
        if k in name: return "residential"
    return "unclassified"

def _step_speed(step, rc):
    d=step.get("distance",0)/1000; t=step.get("duration",0)/3600
    if t>0 and d>0:
        v=d/t
        if 3<v<200: return v
    return ROAD_CLASS_SPEED.get(rc,50)

def cold_start_l(dur_min, specs):
    if specs.get("fuel_type")=="electric": return 0.0
    base=specs.get("cold_start_ml",15)/1000
    if dur_min<=10: return base
    if dur_min<=20: return base*(1-(dur_min-10)/10)
    return 0.0

def hvac_l(dur_hr, temp_c, specs):
    if 18<=temp_c<=24: return 0.0
    intensity=min(1.0,(18-temp_c)/20 if temp_c<18 else (temp_c-24)/16)
    if specs.get("fuel_type")=="electric":
        return (2.0*intensity*dur_hr)/8.9
    return specs.get("hvac_lph",0.8)*intensity*dur_hr

def simulate_fuel(route_data, specs, weather, style_factor):
    idle_l=accel_l=cruise_l=0.0
    try: steps=route_data["segments"][0]["steps"]
    except: return {"idle":0,"accel":0,"cruise":0,"total":0}

    temp_c=weather["temperature_c"] if weather else 15.0
    rho=air_density(temp_c)
    ft=specs.get("fuel_type","gasoline")
    regen=specs.get("regen_fraction",0.0)
    n=len(steps)

    for i,step in enumerate(steps):
        d_km=step.get("distance",0)/1000; t_hr=step.get("duration",0)/3600
        if d_km<=0 or t_hr<=0: continue
        rc=_road_class(step)
        spd=_step_speed(step,rc)
        surf=SURFACE_RR.get(step.get("surface","paved"),1.0)
        precip=(1+min(0.06,weather.get("precipitation_mm",0)*0.012)) if weather else 1.0
        rr=specs["rolling_resistance"]*surf*precip

        # Wind headwind component
        hw=0.0
        if weather and weather.get("wind_speed_kmh",0)>0:
            geom=route_data.get("geometry","")
            coords=decode_polyline(geom) if isinstance(geom,str) and geom else []
            if len(coords)>1:
                si=min(i,len(coords)-2)
                brg=bearing_deg(coords[si][0],coords[si][1],coords[si+1][0],coords[si+1][1])
                ang=math.radians(weather["wind_direction_deg"]-brg)
                hw=weather["wind_speed_kmh"]*math.cos(ang)

        v_air=max(0.5,(spd+hw)/3.6); v_ms=spd/3.6; d_m=d_km*1000
        F_drag=0.5*rho*specs["drag_coefficient"]*specs["frontal_area"]*v_air**2
        F_roll=rr*specs["weight"]*GRAVITY
        F_net=F_drag+F_roll

        # Regen / DFCO credit (zero-grade since we have no elevation)
        regen_credit=0.0

        work_MJ=max(F_net*d_m,0)/1e6
        pw=(F_net*v_ms/1000) if v_ms>0 else 0
        load=1.16 if pw<5 else (0.93 if pw>60 else 1.0)
        combined=load*style_factor

        if ft=="electric":
            seg=(work_MJ/3.6)*combined/specs["efficiency"]/8.9
            seg=max(seg-regen_credit,0)
        else:
            ed=ENERGY_DENSITY_DIESEL if ft=="diesel" else ENERGY_DENSITY_GASOLINE
            seg=max(work_MJ*combined/(ed*specs["efficiency"])-regen_credit,0)

        instr=(step.get("instruction") or "").lower()
        stype=step.get("type",-1)
        is_stop=(any(k in instr for k in ["turn","traffic","junction","roundabout",
                     "merge","exit","ramp","stop","signal","crossing"])
                 or stype in (0,1,2,3,5,6,7,10,11)
                 or rc in ("residential","living_street","service"))

        if spd<5:
            idle_l+=specs["idle_rate"]*t_hr
        elif is_stop:
            n_stops=max(1,d_km/0.4)
            af=specs["accel_cost"]*n_stops*style_factor*(1-regen*0.5)
            accel_l+=af; cruise_l+=seg
        else:
            cruise_l+=seg

    total = idle_l + accel_l + cruise_l

    # Calibrate to EPA figures — anchors absolute values to real-world data
    cal = epa_calibration_factor(specs)
    idle_l   *= cal
    accel_l  *= cal
    cruise_l *= cal
    total     = idle_l + accel_l + cruise_l

    return {"idle":round(idle_l,3),"accel":round(accel_l,3),
            "cruise":round(cruise_l,3),"total":round(total,3)}

def fuel_to_co2(fuel_l, specs):
    ft=specs.get("fuel_type","gasoline")
    if ft=="electric": return round(fuel_l*8.9*CO2_PER_KWH,2)
    if ft=="diesel":   return round(fuel_l*CO2_DIESEL,2)
    return round(fuel_l*CO2_GASOLINE,2)

def fuel_to_cost(fuel_l, specs):
    ft=specs.get("fuel_type","gasoline")
    if ft=="electric": return round(fuel_l*8.9*PRICE_ELECTRICITY,2)
    if ft=="diesel":   return round(fuel_l*PRICE_DIESEL,2)
    return round(fuel_l*PRICE_GASOLINE,2)


def process_route(route, start_addr, end_addr, start_coords, end_coords,
                  specs, name, weather, style_factor):
    dist_km =round(route["summary"]["distance"]/1000,2)
    dur_min =round(route["summary"]["duration"]/60,2)

    geom=route.get("geometry","")
    coords=decode_polyline(geom) if isinstance(geom,str) and geom else []

    steps=[]
    for seg in route.get("segments",[]):
        for st in seg.get("steps",[]):
            if "instruction" in st:
                steps.append({"instruction":st["instruction"],
                               "distance":round(st.get("distance",0)/1000,2),
                               "duration":round(st.get("duration",0)/60,1)})
    if not steps:
        steps=[{"instruction":f"Start at {start_addr}","distance":0,"duration":0},
               {"instruction":f"Drive to {end_addr}","distance":dist_km,"duration":dur_min},
               {"instruction":"Arrive at destination","distance":0,"duration":0}]

    fuel=simulate_fuel(route,specs,weather,style_factor)
    temp_c=weather["temperature_c"] if weather else 15.0
    cs=cold_start_l(dur_min,specs)
    hv=hvac_l(dur_min/60,temp_c,specs)
    total=round(fuel["total"]+cs+hv,3)
    avg_sp=round(dist_km/(dur_min/60),1) if dur_min>0 else 0

    return {"name":name,"start":start_addr,"end":end_addr,
            "distance":dist_km,"duration":dur_min,"total_fuel":total,
            "idle_fuel":fuel["idle"],"accel_fuel":round(fuel["accel"]+cs,3),
            "cruise_fuel":round(fuel["cruise"]+hv,3),
            "fuel_cost":fuel_to_cost(total,specs),"co2_emissions":fuel_to_co2(total,specs),
            "steps":steps,"start_lat":start_coords[0],"start_lng":start_coords[1],
            "end_lat":end_coords[0],"end_lng":end_coords[1],
            "route_coordinates":coords,"avg_speed":avg_sp,"cold_start_l":round(cs,3),"hvac_l":round(hv,3),
            "weather":weather}

# ─── Mock fallback ────────────────────────────────────────────────────────────
def _mock(start_addr,end_addr,start_coords,end_coords,specs):
    dist=haversine_km(*start_coords,*end_coords); dur=dist
    pts=[[start_coords[0]+i/10*(end_coords[0]-start_coords[0]),
          start_coords[1]+i/10*(end_coords[1]-start_coords[1])] for i in range(11)]
    fuel=dist*specs["base_consumption"]
    return {"name":"Estimated Route","tag":"eco","start":start_addr,"end":end_addr,
            "distance":round(dist,2),"duration":round(dur,2),"total_fuel":round(fuel,3),
            "idle_fuel":round(fuel*.1,3),"accel_fuel":round(fuel*.25,3),"cruise_fuel":round(fuel*.65,3),
            "fuel_cost":fuel_to_cost(fuel,specs),"co2_emissions":fuel_to_co2(fuel,specs),
            "steps":[{"instruction":f"Start at {start_addr}","distance":0,"duration":0},
                     {"instruction":f"Drive to {end_addr}","distance":round(dist,2),"duration":round(dur,1)},
                     {"instruction":"Arrive at destination","distance":0,"duration":0}],
            "start_lat":start_coords[0],"start_lng":start_coords[1],
            "end_lat":end_coords[0],"end_lng":end_coords[1],
            "route_coordinates":pts,"avg_speed":60.0,
            "cold_start_l":0.0,"hvac_l":0.0,"weather":None}

def _short_label(item):
    addr=item.get("addressdetails",item.get("address",{})); parts=[]
    for k in ("amenity","building","road","suburb","city","town","village","county","state","country"):
        v=addr.get(k)
        if v and v not in parts: parts.append(v)
        if len(parts)>=3: break
    return ", ".join(parts) if parts else item.get("display_name","")[:60]

# ─── Flask routes ─────────────────────────────────────────────────────────────
@app.route("/")
def index(): return render_template("index.html",makes=get_car_makes())

@app.route("/api/models")
def api_models(): return jsonify(get_car_models(request.args.get("make","")))

@app.route("/api/cars")
def api_cars(): return jsonify(CAR_DATABASE)

@app.route("/api/autocomplete")
def api_autocomplete():
    q=request.args.get("q","").strip()
    if len(q)<2: return jsonify([])
    try:
        r=requests.get("https://nominatim.openstreetmap.org/search",
            params={"q":q,"format":"json","addressdetails":1,"limit":6,"dedupe":1},
            headers={"User-Agent":"MyRoute/2.0"},timeout=5)
        r.raise_for_status()
        return jsonify([{"display":it.get("display_name",""),"short":_short_label(it),
                         "lat":float(it["lat"]),"lon":float(it["lon"])} for it in r.json()])
    except: return jsonify([])

@app.route("/results")
def results():
    start_addr=request.args.get("start",""); end_addr=request.args.get("end","")
    make=request.args.get("make",""); model=request.args.get("model","")
    style=request.args.get("style","normal")
    if not start_addr or not end_addr: return jsonify({"error":"Missing locations"}),400
    specs=get_car_specs(make,model)
    if not specs: return jsonify({"error":f"Unknown vehicle: {make} {model}"}),400
    sf=STYLE_FACTORS.get(style,1.0)

    sl=request.args.get("start_lat"); slo=request.args.get("start_lon")
    el=request.args.get("end_lat");   elo=request.args.get("end_lon")
    sc=(float(sl),float(slo)) if sl and slo else get_coordinates(start_addr)
    ec=(float(el),float(elo)) if el and elo else get_coordinates(end_addr)
    if not sc or not ec: return jsonify({"error":"Could not geocode locations"}),400

    cp=[[sc[1],sc[0]],[ec[1],ec[0]]]
    mid=((sc[0]+ec[0])/2,(sc[1]+ec[1])/2)

    # ── Build the most comprehensive set of ORS calls possible ────────────────
    # ORS public API caps alternative_routes at 3 per call.
    # We combine:
    #   • 5 alternatives calls (different preferences + avoid combos) → up to 15 routes
    #   • 12 via-point calls (4 positions × 3 lateral offsets)       → up to 12 routes
    #   • 3 single-pref calls (fastest/shortest/recommended)         → 3 routes
    # Pool + deduplicate by geometry fingerprint → typically 8–15 unique routes scored.

    via_pts=_generate_via_points(sc,ec,n_along=4,n_perp=3)
    start_ll=[sc[1],sc[0]]; end_ll=[ec[1],ec[0]]

    tasks={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
        # Alternatives pools (up to 3 routes each)
        tasks["alt_rec"]     =ex.submit(_ors_post,_base(cp,"recommended",with_alts=True))
        tasks["alt_fast"]    =ex.submit(_ors_post,_base(cp,"fastest",    with_alts=True))
        tasks["alt_short"]   =ex.submit(_ors_post,_base(cp,"shortest",   with_alts=True))
        tasks["alt_nohwy"]   =ex.submit(_ors_post,_base(cp,"recommended",avoid=["highways"],with_alts=True))
        tasks["alt_notoll"]  =ex.submit(_ors_post,_base(cp,"recommended",avoid=["tollways"],with_alts=True))
        # Single preference calls
        tasks["single_fast"] =ex.submit(_ors_post,_base(cp,"fastest"))
        tasks["single_short"]=ex.submit(_ors_post,_base(cp,"shortest"))
        tasks["single_rec"]  =ex.submit(_ors_post,_base(cp,"recommended"))
        # Via-point forced routes
        for i,via in enumerate(via_pts):
            tasks[f"via_{i}"]=ex.submit(_ors_post,_base([start_ll,via,end_ll],"recommended"))
        # Weather
        tasks["weather"]=ex.submit(fetch_weather,mid[0],mid[1])

    weather=tasks["weather"].result()

    # Collect all raw routes
    raw_pool=[]
    fastest_raw=None
    for k,fut in tasks.items():
        if k=="weather": continue
        result=fut.result()  # always a list from _ors_post
        if not result: continue
        raw_pool.extend(result)
        if k=="single_fast" and result:
            fastest_raw=result[0]  # pin for the Fastest tab

    print(f"[Routes] raw pool={len(raw_pool)}, weather={'OK' if weather else 'FAIL'}")

    if not raw_pool:
        m=_mock(start_addr,end_addr,sc,ec,specs)
        mf=_mock(start_addr,end_addr,sc,ec,specs)
        m["tag"]="eco"; mf["tag"]="fastest"; mf["name"]="Fastest Route"
        def _r(x): return {"name":x["name"],"tag":x["tag"],"distance":x["distance"],
                           "duration":x["duration"],"total_fuel":x["total_fuel"],
                           "co2":x["co2_emissions"],"cost":x["fuel_cost"]}
        return render_template("results.html",start=start_addr,end=end_addr,make=make,
            model=model,style=style,fuel_type=specs.get("fuel_type","gasoline"),specs=specs,
            eco=m,fastest=mf,comparison=[_r(m),_r(mf)],candidates_evaluated=1,
            weather=weather,active_tag="eco")

    # Deduplicate and score every unique route
    unique=_dedupe(raw_pool)
    print(f"[Scoring] {len(unique)} unique routes after deduplication")

    scored=[]
    for i,raw in enumerate(unique):
        p=process_route(raw,start_addr,end_addr,sc,ec,specs,f"Route {i+1}",weather,sf)
        print(f"  Route {i+1}: {p['distance']}km, {p['total_fuel']}L")
        scored.append(p)

    eco=min(scored,key=lambda x:x["total_fuel"])
    eco["tag"]="eco"; eco["name"]="Eco Route"

    if fastest_raw:
        fastest=process_route(fastest_raw,start_addr,end_addr,sc,ec,specs,"Fastest Route",weather,sf)
    else:
        fastest=min(scored,key=lambda x:x["duration"]).copy()
        fastest["name"]="Fastest Route"
    fastest["tag"]="fastest"

    def row(r): return {"name":r["name"],"tag":r["tag"],"distance":r["distance"],
                        "duration":r["duration"],"total_fuel":r["total_fuel"],
                        "co2":r["co2_emissions"],"cost":r["fuel_cost"]}

    return render_template("results.html",start=start_addr,end=end_addr,make=make,
        model=model,style=style,fuel_type=specs.get("fuel_type","gasoline"),specs=specs,
        eco=eco,fastest=fastest,comparison=[row(eco),row(fastest)],
        candidates_evaluated=len(scored),weather=weather,active_tag="eco")

if __name__=="__main__":
    app.run(debug=True)
