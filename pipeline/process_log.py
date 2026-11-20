"""Step 3: process graph, variants and event-level CO2e from ACTIVITIES (data/derived/pe.json).
Event CO2e is the Event_CO2e column; CO2eAllocation says whether carbon sits on its travel event ("Direct") or is "Held at booking"."""
import pandas as pd, numpy as np, json, os
from common import *
e = pd.read_pickle(os.path.join(TMP, 'ev.pkl')).sort_values(['TripID', 'StepOrder'])
t = pd.read_pickle(os.path.join(TMP, 'tripx.pkl')).set_index('TripID')
tot_kg = e.Event_CO2e.sum(); held = e[e.CO2eAllocation == 'Held at booking']
co2 = e.groupby('EventName').Event_CO2e.sum()
print('event t', tot_kg / 1000, '| held at booking', held.Event_CO2e.sum() / 1000, held.Event_CO2e.sum() / tot_kg, '| trips', held.TripID.nunique())
# ---- activities: name, events, trips, event tCO2e
acts = e.EventName.value_counts(); cases = e.groupby('EventName').TripID.nunique()
ACT = [[n, int(acts[n]), int(cases[n]), round(float(co2[n] / 1000), 1)] for n in acts.index]
idx = {a[0]: i for i, a in enumerate(ACT)}
# ---- directly-follows edges with median hours between steps
e['nxt'] = e.groupby('TripID').EventName.shift(-1); e['nts'] = e.groupby('TripID').ts.shift(-1)
df = e.dropna(subset=['nxt']).copy(); df['h'] = (df.nts - df.ts).dt.total_seconds() / 3600
ed = df.groupby(['EventName', 'nxt']).agg(n=('h', 'size'), med=('h', 'median')).reset_index()
first = e.groupby('TripID').EventName.first().value_counts(); last = e.groupby('TripID').EventName.last().value_counts()
EDGES = [[idx[r.EventName], idx[r.nxt], int(r.n), round(float(r.med), 1)] for r in ed.itertuples()]
EDGES += [[-1, idx[k], int(v), 0] for k, v in first.items()] + [[idx[k], -2, int(v), 0] for k, v in last.items()]
# ---- variants
seq = e.groupby('TripID').EventName.apply(lambda x: '|'.join(x)); vc = seq.value_counts(); t['seq'] = seq
chg = t[t.nm2 != ''].seq.value_counts(); up = t[t.nm2.isin(['Business', 'First'])].seq.value_counts(); c2 = t.groupby('seq').tot.sum()
VAR = [[[idx[a] for a in s.split('|')], int(n), int(chg.get(s, 0)), int(up.get(s, 0)), round(float(c2[s] / 1000), 1)] for s, n in vc.head(60).items()]
dom = vc.index[0]; dt = t[t.seq == dom].index; dco = e[e.TripID.isin(dt)].groupby('EventName').Event_CO2e.sum()
DOM = [[a, round(float(dco.get(a, 0) / 1000), 1)] for a in dom.split('|')]
print('variants', len(vc), '| top share', vc.iloc[0] / len(t), '| top10', vc.head(10).sum() / len(t)); print(DOM)
# ---- conformance to the intended order
REF = ['Book Mode of Transportation', 'Submit Travel Request', 'Travel Request Approved', 'Receive Confirmation', 'Submit Expense Request', 'Expense Request Approved', 'Expense Reimbursement']
def conf(s):
    ev = s.split('|'); pos = 0
    for r in REF:
        try: pos = ev.index(r, pos) + 1
        except ValueError: return False
    return True
t['conf'] = seq.map(conf).astype(int); print('conformance', t.conf.mean())
out = dict(ACT=ACT, EDGES=EDGES, VAR=VAR, NVAR=int(len(vc)), DOM=DOM, DOMN=int(vc.iloc[0]), CONF={int(k): int(v) for k, v in t.groupby('cell').conf.sum().items()},
    HELD=round(float(held.Event_CO2e.sum() / tot_kg * 100), 1), HELDT=int(held.TripID.nunique()), NODEP=int(t.dep.isna().sum()), EVT=round(float(tot_kg / 1000)),
    MEDB=[round(float(t[t.OutOfPolicy == 'Yes'].bl.median()), 2), round(float(t[t.OutOfPolicy == 'No'].bl.median()), 2)])
json.dump(out, open(os.path.join(OUT, 'pe.json'), 'w'), separators=(',', ':'))
print('pe KB', os.path.getsize(os.path.join(OUT, 'pe.json')) // 1024, out['MEDB'], out['HELD'], out['HELDT'])
