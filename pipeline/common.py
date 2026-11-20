"""Shared paths and helpers for the pipeline."""
import os, math, sys
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, 'data', 'raw'); TMP = os.path.join(ROOT, 'data', '.cache'); OUT = os.path.join(ROOT, 'data', 'derived')
os.makedirs(TMP, exist_ok=True); os.makedirs(OUT, exist_ok=True)
SOURCES = ['CASES.csv', 'LEGS.csv', 'ACTIVITIES.csv', 'DIM_CITY.csv', 'DIM_MODE.csv']
# Thresholds the app tells its story with
LONG_HAUL_KM = 3700      # BEIS long-haul boundary
MID_HAUL_KM = 1500
CORRIDOR_KM = 1200       # rail corridor limit
FARE_MULT = 2.5          # premium fare = 2.5 x economy fare (Celonis premium_fare_multiple); sets directional cabin dollars

def need_sources():
    miss = [f for f in SOURCES if not os.path.exists(os.path.join(RAW, f))]
    if miss: sys.exit('Missing in data/raw/: ' + ', '.join(miss))

def city_coords():
    c = pd.read_csv(os.path.join(RAW, 'DIM_CITY.csv'), keep_default_na=False)
    return {r.City: (r.Latitude, r.Longitude) for r in c.itertuples()}

def great_circle(coords, p, q):
    (a1, b1), (a2, b2) = coords[p], coords[q]; r = math.radians
    d = math.sin(r(a2 - a1) / 2) ** 2 + math.cos(r(a1)) * math.cos(r(a2)) * math.sin(r(b2 - b1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(d))
