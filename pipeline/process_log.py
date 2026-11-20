"""Step 3: process graph, variants and event-level CO2e from Trip_Event_Log (data/derived/pe.json)."""
import pandas as pd, numpy as np, json
import os, sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
RAW=os.path.join(ROOT,'data','raw'); TMP=os.path.join(ROOT,'data','.cache'); OUT=os.path.join(ROOT,'data','derived')
os.makedirs(TMP,exist_ok=True); os.makedirs(OUT,exist_ok=True); sys.path.insert(0,HERE)
e=pd.read_pickle(os.path.join(TMP,'ev.pkl')).sort_values(['TripID','StepOrder'])
t=pd.read_pickle(os.path.join(TMP,'tripx.pkl')).set_index('TripID'); l=pd.read_pickle(os.path.join(TMP,'legsx.pkl'))
# ---- event CO2e allocation
fam=np.where(l.ShippingTypeDescription.str.contains('Flight'),'F',np.where(l.ShippingTypeDescription=='Train','T','C'))
l['fam']=fam
lk=l.groupby(['TripID','fam']).kg.sum().unstack(fill_value=0)
has=e.groupby(['TripID','EventName']).size().unstack(fill_value=0)>0
EVMAP={'F':('Take Departure Flight','Take Return Flight'),'T':('Take Departure Train','Take Return Train'),'C':('Pickup Rental','Return Rental')}
alloc={}  # (TripID,EventName)->kg  (first occurrence)
rem=pd.Series(0.0,index=t.index)
for f,(d,r) in EVMAP.items():
    if f not in lk: continue
    k=lk[f].reindex(t.index).fillna(0)
    hd=has[d].reindex(t.index).fillna(False) if d in has else pd.Series(False,index=t.index)
    hr=has[r].reindex(t.index).fillna(False) if r in has else pd.Series(False,index=t.index)
    alloc[d]=np.where(hd,k/2,0);alloc[r]=np.where(hr,k/2,0)
    rem+=np.where(hd,0,k/2)+np.where(hr,0,k/2)
hl=has['Book Lodging'].reindex(t.index).fillna(False)
alloc['Book Lodging']=np.where(hl,t.hkg,0);rem+=np.where(hl,0,t.hkg)
alloc['Book Mode of Transportation']=rem.values
A=pd.DataFrame(alloc,index=t.index)
print('alloc total t',A.values.sum()/1000,'trip total',t.tot.sum()/1000,'held share',A['Book Mode of Transportation'].sum()/A.values.sum())
print((A.sum()/1000).round())
held_trips=int((rem>1).sum())
# ---- activities
acts=e.EventName.value_counts()
cases=e.groupby('EventName').TripID.nunique()
ACT=[[n,int(acts[n]),int(cases[n]),round(float(A[n].sum()/1000) if n in A else 0,1)] for n in acts.index]
idx={a[0]:i for i,a in enumerate(ACT)}
# ---- directly follows edges
e['nxt']=e.groupby('TripID').EventName.shift(-1);e['nts']=e.groupby('TripID').ts.shift(-1)
df=e.dropna(subset=['nxt']).copy();df['h']=(df.nts-df.ts).dt.total_seconds()/3600
ed=df.groupby(['EventName','nxt']).agg(n=('h','size'),med=('h','median')).reset_index()
first=e.groupby('TripID').EventName.first().value_counts();last=e.groupby('TripID').EventName.last().value_counts()
EDGES=[[idx[r.EventName],idx[r.nxt],int(r.n),round(float(r.med),1)] for r in ed.itertuples()]
EDGES+=[[-1,idx[k],int(v),0] for k,v in first.items()]+[[idx[k],-2,int(v),0] for k,v in last.items()]
# ---- variants
seq=e.groupby('TripID').EventName.apply(lambda x:'|'.join(x))
vc=seq.value_counts()
t['seq']=seq
chg=t[t.nm2!=''].seq.value_counts();up=t[t.nm2.isin(['Business','First'])].seq.value_counts()
co2=t.groupby('seq').tot.sum()
VAR=[[[idx[a] for a in s.split('|')],int(n),int(chg.get(s,0)),int(up.get(s,0)),round(float(co2[s]/1000),1)] for s,n in vc.head(60).items()]
print('variants',len(vc),'top share',vc.iloc[0]/len(t), 'top10',vc.head(10).sum()/len(t))
# dominant variant step co2e
dom=vc.index[0];dt=t[t.seq==dom].index
DOM=[[a,round(float(A.loc[dt,a].sum()/1000),1) if a in A else 0] for a in dom.split('|')]
print(DOM)
# conformance: reference order subsequence
REF=['Book Mode of Transportation','Submit Travel Request','Travel Request Approved','Receive Confirmation','Submit Expense Request','Expense Request Approved','Expense Reimbursement']
def conf(s):
    ev=s.split('|');pos=0
    for r in REF:
        try: pos=ev.index(r,pos)+1
        except ValueError: return False
    return True
cf=seq.map(conf);print('conformance',cf.mean())
t['conf']=cf.astype(int)
# per cell conformance + no-departure
cc=t.groupby('cell').conf.sum()
# throughput medians
out=dict(ACT=ACT,EDGES=EDGES,VAR=VAR,NVAR=int(len(vc)),DOM=DOM,DOMN=int(vc.iloc[0]),CONF={int(k):int(v) for k,v in cc.items()},
  HELD=round(float(A['Book Mode of Transportation'].sum()/A.values.sum()*100),1),HELDT=int(held_trips),EVT=round(float(A.values.sum()/1000)),
  MEDB=[round(float(t[t.OutOfPolicy=='Yes'].bl.median()),2),round(float(t[t.OutOfPolicy=='No'].bl.median()),2)])
json.dump(out,open(os.path.join(OUT,'pe.json'),'w'),separators=(',',':'))
import os;print('pe KB',os.path.getsize(os.path.join(OUT,'pe.json'))//1024, out['MEDB'], out['HELD'], out['HELDT'])
