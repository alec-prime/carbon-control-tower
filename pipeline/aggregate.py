"""Step 2: build the filterable data cube (data/derived/data.json) straight from CASES, LEGS and ACTIVITIES.
No emissions are modelled or calibrated here: every tCO2e figure is the value in the source tables."""
import pandas as pd, numpy as np, json, os
from common import *
t = pd.read_pickle(os.path.join(TMP, 'cases.pkl')); l = pd.read_pickle(os.path.join(TMP, 'legs.pkl')); e = pd.read_pickle(os.path.join(TMP, 'ev.pkl'))
chk = json.load(open(os.path.join(TMP, 'checks.json'))); coords = city_coords()
R = ['Asia Pacific', 'Latin America', 'North America', 'Middle East & Africa', 'Europe']
assert set(t.DepartureRegion) == set(R), set(t.DepartureRegion)
t['reg'] = t.DepartureRegion
# ---- legs
l['km'] = l.distance_km; l['flight'] = l.ModeFamily.eq('Air')
l['cabin'] = l.CabinTier.map({'Economy': 'E', 'Business': 'B', 'First': 'F'}).fillna('')
l['kg'] = l.Leg_CO2e                                                    # departure + return
l['econkg'] = np.where(l.flight, l.Alt_Economy_Leg_CO2e.fillna(l.Leg_CO2e), l.Leg_CO2e)   # same route in economy (economy legs are their own alternative)
l['trainkg'] = l.Alt_Rail_Leg_CO2e.fillna(0)                            # same route by rail
l['seg'] = l.DepartureLocationCity + ' – ' + l.ArrivalLocationCity
airkm = l[l.flight].groupby('seg').km.median()
segkm = lambda s: float(airkm[s]) if s in airkm.index else great_circle(coords, *s.split(' – '))
# corridor = a route with at least one train leg in our own bookings and a flight distance under 1,200 km
trainseg = sorted(l[l.ModeFamily == 'Rail'].seg.unique())
corr = [s for s in trainseg if segkm(s) < CORRIDOR_KM]; l['corr'] = l.seg.isin(corr)
fl = l[l.flight].copy()
fl['isP'] = (fl.IsPremium == 1).astype(int); fl['isL'] = (fl.km > LONG_HAUL_KM).astype(int); fl['isC'] = fl['corr'].astype(int)
fl['isM'] = ((fl.km >= MID_HAUL_KM) & (fl.km <= LONG_HAUL_KM)).astype(int); fl['isS'] = (fl.km < MID_HAUL_KM).astype(int); fl['one'] = 1
fl['premkg'] = fl.kg * fl.isP; fl['upl'] = fl.kg - fl.econkg; fl['lhkg'] = fl.kg * fl.isL; fl['corrkg'] = fl.kg * fl.isC
fl['k1'] = fl.lhkg; fl['k2'] = fl.kg * fl.isM; fl['k3'] = fl.kg * fl.isS
fl['cdiff'] = np.where(fl.isP == 1, fl.TripCosts * (1 - 1 / FARE_MULT), 0)   # directional: premium fare minus the economy fare it implies
tf = fl.groupby('TripID').agg(flegs=('one', 'sum'), prem=('isP', 'sum'), lhlegs=('isL', 'sum'), corrlegs=('isC', 'sum'), fkg=('kg', 'sum'), premkg=('premkg', 'sum'), upl=('upl', 'sum'),
    lhkg=('lhkg', 'sum'), corrkg=('corrkg', 'sum'), b1=('isL', 'sum'), b2=('isM', 'sum'), b3=('isS', 'sum'), k1=('k1', 'sum'), k2=('k2', 'sum'), k3=('k3', 'sum'), cabdol=('cdiff', 'sum'))
t = t.join(tf, on='TripID').fillna({c: 0 for c in tf.columns})
t['tkg'] = t.Transportation_CO2e; t['hkg'] = t.Hotel_CO2e; t['tot'] = t.Total_CO2e; t['nonfkg'] = t.tkg - t.fkg
t['trains'] = t.TripID.map(l[l.ModeFamily == 'Rail'].groupby('TripID').size()).fillna(0)
t['lh'] = (t.lhlegs > 0).astype(int); t['internal'] = (t.Purpose == 'Internal Business Trip').astype(int); t['oop'] = (t.OutOfPolicy == 'Yes').astype(int)
NEWMODE = {'Updated Economy Flight': 'Economy', 'Updated Business Class Flight': 'Business', 'Updated First Class Flight': 'First', 'Updated Train': 'Train'}
t['nm2'] = t.NewModeOfTransportation.map(lambda x: NEWMODE.get(x, 'Car') if isinstance(x, str) else '')
t['score'] = (t.prem > 0).astype(int) + ((t.internal == 1) & (t.flegs > 0)).astype(int) + (t.corrlegs > 0).astype(int) + (t.lh == 1).astype(int)
# ---- booking clock and approval come from the event log
_b = e[e.EventName == 'Book Mode of Transportation'].groupby('TripID').ts.min()
_d = e[e.EventName.isin(['Take Departure Flight', 'Take Departure Train', 'Pickup Rental'])].groupby('TripID').ts.min()
_a = e[e.EventName == 'Travel Request Approved'].groupby('TripID').size()
t['book'] = t.TripID.map(_b); t['dep'] = t.TripID.map(_d); t['appr'] = (t.TripID.map(_a).fillna(0) > 0).astype(int)
t['bl'] = (t.dep - t.book).dt.total_seconds() / 86400
MONTHS = ['2023-12'] + [f'2024-{m:02d}' for m in range(1, 13)] + ['2025']
t['mo'] = pd.to_datetime(t.BookingMonth).dt.strftime('%Y-%m').map(lambda x: MONTHS.index(x) if x in MONTHS else len(MONTHS) - 1)
lbk = np.select([t.bl.isna(), t.bl < 3, t.bl < 7, t.bl < 14], [4, 0, 1, 2], 3)
for i in range(5): t[f'lb{i}'] = (lbk == i).astype(int); t[f'lo{i}'] = ((lbk == i) & (t.oop == 1)).astype(int)
t['oopAppr'] = ((t.oop == 1) & (t.appr == 1)).astype(int)
NMO = len(MONTHS)
BU = list(t.BusinessUnit.value_counts().index); P = list(t.Purpose.value_counts().index)
t['ri'] = t.reg.map(R.index); t['bi'] = t.BusinessUnit.map(BU.index); t['pi'] = t.Purpose.map(P.index)
t['cell'] = (((t.ri * len(BU) + t.bi) * len(P) + t.pi) * 2 + t.lh) * NMO + t.mo
M = ['trips', 'tot', 'tkg', 'hkg', 'spend', 'oop', 'flegs', 'prem', 'premkg', 'fkg', 'upl', 'lhlegs', 'lhkg', 'corrlegs', 'corrkg', 'trains', 'b1', 'b2', 'b3', 'k1', 'k2', 'k3', 'internal', 'intkg', 'intflown', 'nonfkg', 'cabdol',
     'nmE', 'nmB', 'nmF', 'nmT', 'nmC', 'oopE', 'oopB', 'oopF', 'oopT', 'oopC', 'nochgkg', 's2', 's2kg', 's0', 'intlh', 'lhint_kg', 'appr', 'oopAppr', 'lb0', 'lb1', 'lb2', 'lb3', 'lb4', 'lo0', 'lo1', 'lo2', 'lo3', 'lo4']
t['trips'] = 1; t['spend'] = t.NetCosts; t['intkg'] = t.tot * t.internal; t['intflown'] = ((t.internal == 1) & (t.flegs > 0)).astype(int)
for k, c in zip('EBFTC', ['Economy', 'Business', 'First', 'Train', 'Car']):
    t['nm' + k] = (t.nm2 == c).astype(int); t['oop' + k] = ((t.nm2 == c) & (t.oop == 1)).astype(int)
t['nochgkg'] = np.where(t.nm2 == '', t.tot, 0); t['s2'] = (t.score >= 2).astype(int); t['s2kg'] = t.tot * t.s2; t['s0'] = (t.score == 0).astype(int)
t['intlh'] = t.internal * t.lh; t['lhint_kg'] = t.tot * t.internal * t.lh
cube = t.groupby('cell')[M].sum()
cells = {int(c): [round(float(v), 1) for v in row] for c, row in cube.iterrows()}
# ---- routes
t['route'] = t.DepartureLocationCity + ' → ' + t.ArrivalLocationCity
RT = list(t.route.value_counts().index); t['rti'] = t.route.map(RT.index)
rc = t.groupby(['cell', 'rti']).agg(n=('trips', 'sum'), kg=('tot', 'sum'), ni=('internal', 'sum')).reset_index()
routes = [[int(r.cell), int(r.rti), int(r.n), round(r.kg / 1000, 2), int(r.ni)] for r in rc.itertuples()]
rmeta = []
for r in RT:
    d, ar = r.split(' → '); rmeta.append([r, round(segkm(f'{d} – {ar}')), t[t.route == r].ArrivalLocationCountry.iloc[0]])
# ---- corridor segments by cell
cl = l[l['corr'] & (l.flight | (l.ModeFamily == 'Rail'))].merge(t[['TripID', 'cell']], on='TripID')   # flights and trains only; car legs on the same pair are not rail
cc = cl.groupby(['cell', 'seg']).agg(f=('flight', 'sum'), n=('flight', 'size')).reset_index()
corridors = [[int(r.cell), corr.index(r.seg), int(r.f), int(r.n - r.f)] for r in cc.itertuples()]
cmeta = [[s, round(segkm(s))] for s in corr]
# ---- policy segments: flights by cell x segment x cabin (what the Policy Impact engine sums)
fl2 = fl.merge(t[['TripID', 'cell']], on='TripID')
SG = sorted(fl2.seg.unique())
ps = fl2.groupby(['cell', 'seg', 'cabin']).agg(n=('kg', 'size'), kg=('kg', 'sum'), ek=('econkg', 'sum'), tk=('trainkg', 'sum'), cd=('cdiff', 'sum')).reset_index()
pseg = [[int(r.cell), SG.index(r.seg), 'EBF'.index(r.cabin), int(r.n), round(r.kg / 1000, 4), round(r.ek / 1000, 4), round(r.tk / 1000, 4), round(r.cd)] for r in ps.itertuples()]
smeta = [[s, round(segkm(s)), s in corr] for s in SG]
# ---- breach queue: trips breaking 2+ of the four rules
bl_ = t[t.score >= 2].sort_values(['score', 'tot'], ascending=[False, False]).head(400)
breach = [[int(r.TripID), int(r.cell), int(r.score), round(r.tot / 1000, 2), int(r.oop)] for r in bl_.itertuples()]
pc = t.groupby('ProcessCode').agg(all=('trips', 'sum'), chg=('nm2', lambda x: (x != '').sum()), up=('nm2', lambda x: x.isin(['Business', 'First']).sum()))
variants = [[k, int(r['all']), int(r.chg), int(r.up)] for k, r in pc.iterrows()]
# ---- facts the Data Trust view and footnotes quote (all computed, none typed in)
prem = fl[fl.isP == 1]; trn = l[l.ModeFamily == 'Rail']
miss = [[s, int((trn.seg == s).sum()), round(segkm(s))] for s in trainseg if s not in corr]
bd = fl[fl.seg == 'Beijing – New Delhi']
an = l[l.IsAnomalousRoute == 1]
FACTS = dict(trips=int(len(t)), legs=int(len(l)), events=int(len(e)), legsT=chk['legs_t'], transT=chk['cases_transport_t'], hotelT=chk['cases_hotel_t'], totT=chk['cases_total_t'], eventsT=chk['events_t'],
    tripLegDiff=chk['trip_leg_maxdiff_kg'], tripEvDiff=chk['trip_event_maxdiff_kg'], legsNoTrip=chk['legs_without_trip'], tripsNoLegs=chk['trips_without_legs'], modeMismatch=chk['legs_mode_attr_mismatch'] + chk['legs_mode_not_in_dim'],
    airKmMaxDiff=chk['air_km_maxdiff'], lhLegsDist=chk['lh_legs_dist'], lhTripsDist=chk['lh_trips_dist'], lhLegsGc=chk['lh_legs_gc'], lhTripsGc=chk['lh_trips_gc'],
    cabinUplift=float(prem.upl.sum() / 1000), cabinUpliftCases=float(t.CabinCapSaving_CO2e.sum() / 1000), premCost=float(prem.TripCosts.sum()), cabinDollars=float(fl.cdiff.sum()),
    corrLegs=int(fl.isC.sum()), missCorr=miss, flagged=[[r.RouteLabel, r.ShippingTypeDescription] for r in an.itertuples()], nFlagged=int(len(an)),
    bdKm=round(float(bd.km.median())), bdLegs=int(len(bd)), medConfBreach=float(t[t.oop == 1].LeadTimeDays.median()), medConfOk=float(t[t.oop == 0].LeadTimeDays.median()),
    sameRoute=float((prem.AltEconomyBasis == 'Same route economy factor').mean()), fareMult=FARE_MULT, regions={r: float(t[t.reg == r].tot.sum() / 1000) for r in R})
out = dict(MONTHS=MONTHS, NM=NMO, R=R, BU=BU, P=P, M=M, cells=cells, RT=rmeta, routes=routes, CS=cmeta, corridors=corridors, SG=smeta, pseg=pseg, breach=breach, variants=variants, FACTS=FACTS)
json.dump(out, open(os.path.join(OUT, 'data.json'), 'w'), separators=(',', ':'), default=float)
t[['TripID', 'book', 'dep', 'bl', 'appr', 'mo', 'cell', 'tot', 'hkg', 'nm2', 'OutOfPolicy', 'ri', 'bi', 'pi', 'lh']].to_pickle(os.path.join(TMP, 'tripx.pkl'))
print('data.json KB', os.path.getsize(os.path.join(OUT, 'data.json')) // 1024, '| cells', len(cells), 'pseg', len(pseg), 'routes', len(routes))
print('total t', t.tot.sum() / 1000, '| transport', t.tkg.sum() / 1000, '| hotel', t.hkg.sum() / 1000)
print(t.groupby('reg').tot.sum().div(1000).round(0).to_dict())
print('corridors', corr); print('corridor flight legs', int(fl.isC.sum()), 'rail share', len(l[l['corr'] & ~l.flight & (l.ModeFamily == 'Rail')]) / len(l[l['corr'] & (l.flight | (l.ModeFamily == 'Rail'))]))
print('missing from corridor list', miss, '| flagged', FACTS['flagged'])
print('premium legs', int(fl.isP.sum()), 'share', t.premkg.sum() / t.fkg.sum(), '| uplift t', FACTS['cabinUplift'], 'cases', FACTS['cabinUpliftCases'], '| cabin $', FACTS['cabinDollars'])
print('LH legs', int(fl.isL.sum()), 'LH trips', int(t.lh.sum()), 'LH t share', t[t.lh == 1].tot.sum() / t.tot.sum(), '| Beijing-Delhi', FACTS['bdKm'], FACTS['bdLegs'])
print('oop', t.oop.mean(), 'oop approved', t.oopAppr.sum() / t.oop.sum(), '| lead buckets of breaches', (t[[f'lo{i}' for i in range(5)]].sum() / t.oop.sum()).round(3).to_dict())
print('median days breach/ok, booking clock', t[t.oop == 1].bl.median(), t[t.oop == 0].bl.median(), '| confirmation clock', FACTS['medConfBreach'], FACTS['medConfOk'])
print('score>=2', int(t.s2.sum()), t.s2kg.sum() / t.tot.sum(), 's0', int(t.s0.sum()), '| internal LH', t[t.internal == 1].lh.mean())
for c in ['Business', 'First', 'Economy', 'Train', 'Car']: print(c, int((t.nm2 == c).sum()), round(t[t.nm2 == c].oop.mean(), 3))
