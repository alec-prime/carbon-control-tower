"""Step 1: distance-based leg emissions (great-circle km x BEIS-style factors). Reads data/raw, writes data/.cache."""
import pandas as pd, glob, numpy as np, json, math
import os, sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
RAW=os.path.join(ROOT,'data','raw'); TMP=os.path.join(ROOT,'data','.cache'); OUT=os.path.join(ROOT,'data','derived')
os.makedirs(TMP,exist_ok=True); os.makedirs(OUT,exist_ok=True); sys.path.insert(0,HERE)
t=pd.read_csv(os.path.join(RAW,'Trip_Data_No_Emissions.csv')); l=pd.read_csv(os.path.join(RAW,'Transportations_Data_No_Emissions.csv')); a=pd.read_csv(os.path.join(RAW,'Trip_Event_Attributes.csv'))
from coords import C,hv
missing={c for c in set(l.DepartureLocationCity)|set(l.ArrivalLocationCity) if c not in C}; assert not missing,missing
l['km']=[hv(x,y) for x,y in zip(l.DepartureLocationCity,l.ArrivalLocationCity)]
m=l.ShippingTypeDescription
l['flight']=m.str.contains('Flight'); l['cabin']=np.select([m.str.startswith('Business'),m.str.startswith('First'),m.str.startswith('Economy')],['B','F','E'],'')
l['dom']=l.DepartureLocationCountry==l.ArrivalLocationCountry
l['haul']=np.where(~l.flight,'',np.where(l.km>3700,'L',np.where(l.dom,'D','S')))
base={'D':0.246,'S':0.151,'L':0.148}; mult={'D':{'E':1,'B':1.5,'F':1.5},'S':{'E':1,'B':1.5,'F':1.5},'L':{'E':1,'B':2.9,'F':4.0}}
car={'Train':0.0355,'BMW 3 diesel':0.171,'Volkswagen Golf diesel':0.171,'Volkswagen Golf petrol':0.164,'BMW 3 plugin hybrid':0.071,'Fiat 500 electric':0.047}
def f(r):
    if r.flight: return base[r.haul]*mult[r.haul][r.cabin]*1.08
    return car[r.ShippingTypeDescription]
l['fac']=l.apply(f,axis=1)
l['econfac']=[base[h]*1.08 if fl else fc for h,fl,fc in zip(l.haul,l.flight,l.fac)]
l['kg']=l.km*l.fac*2; l['econkg']=l.km*l.econfac*2
print('raw transport t',l.kg.sum()/1000)
fl=l[l.flight]
print('flights',len(fl),'LH legs',(fl.km>3700).sum(),(fl.km>3700).mean())
print('premium share leg emissions',fl[fl.cabin!='E'].kg.sum()/fl.kg.sum(),'uplift share',(fl.kg-fl.econkg).sum()/l.kg.sum())
t['route']=t.DepartureLocationCity+' → '+t.ArrivalLocationCity
k=l.groupby('TripID').kg.sum(); t['tkg']=t.TripID.map(k)
print((t.groupby('route').tkg.sum()/l.kg.sum()).sort_values(ascending=False).head(10))
lh=fl[fl.km>3700].TripID.unique(); print('LH trips',len(lh),'LH share', t[t.TripID.isin(lh)].tkg.sum()/t.tkg.sum())
l.to_pickle(os.path.join(TMP,'legs.pkl')); t.to_pickle(os.path.join(TMP,'trips.pkl')); a.to_pickle(os.path.join(TMP,'attr.pkl'))
# event log, parsed once
e=pd.read_csv(os.path.join(RAW,'Trip_Event_Log.csv'))
e['ts']=pd.to_datetime(e.EventTimestamp,format='%m/%d/%Y %H:%M:%S')
e.to_pickle(os.path.join(TMP,'ev.pkl'))
