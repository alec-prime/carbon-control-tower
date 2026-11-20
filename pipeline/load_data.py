"""Step 1: load the five source tables from data/raw, reconcile them, cache typed copies in data/.cache."""
import pandas as pd, numpy as np, json, os
from common import *
need_sources()
rd = lambda f, **k: pd.read_csv(os.path.join(RAW, f), **k)
cases = rd('CASES.csv'); legs = rd('LEGS.csv'); ev = rd('ACTIVITIES.csv')
city = rd('DIM_CITY.csv', keep_default_na=False); mode = rd('DIM_MODE.csv')
print('rows: cases', len(cases), 'legs', len(legs), 'events', len(ev), 'cities', len(city), 'modes', len(mode))
chk = {}
# ---- keys
assert not cases.TripID.duplicated().any(), 'duplicate TripID in CASES'
chk['legs_without_trip'] = int((~legs.TripID.isin(cases.TripID)).sum())
chk['trips_without_legs'] = int((~cases.TripID.isin(legs.TripID)).sum())
chk['events_without_trip'] = int((~ev.TripID.isin(cases.TripID)).sum())
# ---- DIM_MODE: every leg's mode attributes must agree with the dimension
m = legs.merge(mode, on='ShippingTypeDescription', how='left', suffixes=('', '_dim'))
chk['legs_mode_not_in_dim'] = int(m.ModeFamily_dim.isna().sum())
chk['legs_mode_attr_mismatch'] = int(sum((m[k] != m[k + '_dim']).sum() for k in ['ModeFamily', 'CabinTier', 'FuelType', 'IsPremium']))
# ---- DIM_CITY: every city used must have coordinates and a country that matches the data
coords = city_coords()
used = set(legs.DepartureLocationCity) | set(legs.ArrivalLocationCity) | set(cases.DepartureLocationCity) | set(cases.ArrivalLocationCity)
chk['cities_not_in_dim'] = sorted(used - set(coords))
cc = city.set_index('City').Country
chk['city_country_mismatch'] = int(sum(cc.get(c) != k for c, k in zip(legs.ArrivalLocationCity, legs.ArrivalLocationCountry)) + sum(cc.get(c) != k for c, k in zip(legs.DepartureLocationCity, legs.DepartureLocationCountry)))
assert not chk['cities_not_in_dim'], chk['cities_not_in_dim']
# ---- emissions reconcile at three levels
chk['legs_t'] = legs.Leg_CO2e.sum() / 1000; chk['cases_transport_t'] = cases.Transportation_CO2e.sum() / 1000
chk['cases_hotel_t'] = cases.Hotel_CO2e.sum() / 1000; chk['cases_total_t'] = cases.Total_CO2e.sum() / 1000; chk['events_t'] = ev.Event_CO2e.sum() / 1000
chk['trip_leg_maxdiff_kg'] = float(legs.groupby('TripID').Leg_CO2e.sum().sub(cases.set_index('TripID').Transportation_CO2e).abs().max())
chk['trip_event_maxdiff_kg'] = float(ev.groupby('TripID').Event_CO2e.sum().sub(cases.set_index('TripID').Total_CO2e).abs().max())
chk['leg_return_eq_departure'] = bool(np.allclose(legs.Leg_CO2e, legs.Departure_CO2e + legs.Return_CO2e))
# ---- great-circle recount of air legs from DIM_CITY vs the distance_km column
air = legs[legs.ModeFamily == 'Air'].copy()
air['gc'] = [great_circle(coords, p, q) for p, q in zip(air.DepartureLocationCity, air.ArrivalLocationCity)]
chk['air_legs'] = int(len(air)); chk['air_km_maxdiff'] = float((air.gc - air.distance_km).abs().max())
for k, col in (('dist', 'distance_km'), ('gc', 'gc')):
    lh = air[air[col] > LONG_HAUL_KM]; chk[f'lh_legs_{k}'] = int(len(lh)); chk[f'lh_trips_{k}'] = int(lh.TripID.nunique())
print(json.dumps(chk, indent=1, default=float))
ev['ts'] = pd.to_datetime(ev.EventTimestamp)
cases.to_pickle(os.path.join(TMP, 'cases.pkl')); legs.to_pickle(os.path.join(TMP, 'legs.pkl')); ev.to_pickle(os.path.join(TMP, 'ev.pkl'))
json.dump(chk, open(os.path.join(TMP, 'checks.json'), 'w'), default=float)
