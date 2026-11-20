"""Step 2: calibrate to pipeline totals and build the filterable data cube (data/derived/data.json)."""
import pandas as pd, numpy as np, json, sys
import os, sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
RAW=os.path.join(ROOT,'data','raw'); TMP=os.path.join(ROOT,'data','.cache'); OUT=os.path.join(ROOT,'data','derived')
os.makedirs(TMP,exist_ok=True); os.makedirs(OUT,exist_ok=True); sys.path.insert(0,HERE)
from coords import C,hv
l=pd.read_pickle(os.path.join(TMP,'legs.pkl')); t=pd.read_pickle(os.path.join(TMP,'trips.pkl')); a=pd.read_pickle(os.path.join(TMP,'attr.pkl'))
S=226485e3/l.kg.sum(); l['kg']*=S; l['econkg']*=S
l['trainkg']=l.km*0.0355*2*S
t['hkg']=t.HotelNights/t.HotelNights.sum()*6496e3
REG={'AU':'Asia Pacific','CN':'Asia Pacific','JP':'Asia Pacific','BR':'Latin America','US':'North America','MX':'North America','DE':'Europe','ES':'Europe','ZA':'Middle East & Africa'}
t['reg']=t.DepartureLocationCountry.map(REG)
TGT={'Asia Pacific':155803,'Latin America':52603,'North America':18266,'Middle East & Africa':1077,'Europe':5232}
l['reg']=l.TripID.map(t.set_index('TripID').reg)
pre=(l.groupby('reg').kg.sum()+t.groupby('reg').hkg.sum())/1000
fac={r:TGT[r]/pre[r] for r in TGT}
l['kg']*=l.reg.map(fac);l['econkg']*=l.reg.map(fac);l['trainkg']*=l.reg.map(fac);t['hkg']*=t.reg.map(fac)
fl0=l[l.flight];u=76976e3/(fl0.kg-fl0.econkg).sum()
l['econkg']=np.where(l.flight,l.kg-(l.kg-l.econkg)*u,l.econkg)
print('region factors',fac,'uplift factor',u)
l['seg']=l.DepartureLocationCity+' – '+l.ArrivalLocationCity
# corridors: segments under 1200 km with at least one train leg in bookings
trainseg=l[l.ShippingTypeDescription=='Train'].groupby('seg').km.first()
corr=sorted(trainseg[trainseg<1200].index); l['corr']=l.seg.isin(corr)
fl=l[l.flight].copy()
# trip-level flags
fl['isP']=(fl.cabin!='E').astype(int);fl['isL']=(fl.km>3700).astype(int);fl['isC']=fl['corr'].astype(int)
fl['isM']=((fl.km>=1500)&(fl.km<=3700)).astype(int);fl['isS']=(fl.km<1500).astype(int);fl['one']=1
fl['premkg']=fl.kg*fl.isP;fl['upl']=fl.kg-fl.econkg;fl['lhkg']=fl.kg*fl.isL;fl['corrkg']=fl.kg*fl.isC
fl['k1']=fl.lhkg;fl['k2']=fl.kg*fl.isM;fl['k3']=fl.kg*fl.isS
tf=fl.groupby('TripID').agg(flegs=('one','sum'),prem=('isP','sum'),lhlegs=('isL','sum'),corrlegs=('isC','sum'),fkg=('kg','sum'),premkg=('premkg','sum'),upl=('upl','sum'),lhkg=('lhkg','sum'),corrkg=('corrkg','sum'),
 b1=('isL','sum'),b2=('isM','sum'),b3=('isS','sum'),k1=('k1','sum'),k2=('k2','sum'),k3=('k3','sum'))
t=t.join(tf,on='TripID').fillna({c:0 for c in tf.columns})
t['tkg']=t.TripID.map(l.groupby('TripID').kg.sum()).fillna(0)
t['trains']=t.TripID.map(l[l.ShippingTypeDescription=='Train'].groupby('TripID').size()).fillna(0)
t['nonfkg']=t.tkg-t.fkg
t['tot']=t.tkg+t.hkg
t['lh']=(t.lhlegs>0).astype(int); t['internal']=(t.Purpose=='Internal Business Trip').astype(int)
t['oop']=(t.OutOfPolicy=='Yes').astype(int)
a=a.set_index('TripID'); t['nm']=t.TripID.map(a.NewModeOfTransportation)
NM={'Updated Economy Flight':'Economy','Updated Business Class Flight':'Business','Updated First Class Flight':'First','Updated Train':'Train'}
t['nm2']=t.nm.map(lambda x: NM.get(x,'Car') if isinstance(x,str) else '')
t['pcode']=t.TripID.map(a.ProcessCode)
t['score']=(t.prem>0).astype(int)+((t.internal==1)&(t.flegs>0)).astype(int)+(t.corrlegs>0).astype(int)+(t.lh==1).astype(int)
# cabin dollars: premium leg cost minus avg economy cost on same segment
ec=l[l.cabin=='E'].groupby('seg').TripCosts.mean()
fl['ecost']=fl.seg.map(ec); fl['cdiff']=np.where(fl.cabin!='E',fl.TripCosts-fl.ecost.fillna(fl.TripCosts),0); fl['cdiff']*=72533278/fl.cdiff.sum()
t['cabdol']=t.TripID.map(fl.groupby('TripID').cdiff.sum()).fillna(0)
print('cabin dollars',t.cabdol.sum(),'uplift t',t.upl.sum()/1000, 'LH share',t[t.lh==1].tot.sum()/t.tot.sum())
print(t.groupby('reg').tot.sum()/1000)
R=['Asia Pacific','Latin America','North America','Middle East & Africa','Europe']
BU=list(t.BusinessUnit.value_counts().index); P=list(t.Purpose.value_counts().index)
t['ri']=t.reg.map(R.index); t['bi']=t.BusinessUnit.map(BU.index); t['pi']=t.Purpose.map(P.index)
e=pd.read_pickle(os.path.join(TMP,'ev.pkl'))
_b=e[e.EventName=='Book Mode of Transportation'].groupby('TripID').ts.min()
_d=e[e.EventName.isin(['Take Departure Flight','Take Departure Train','Pickup Rental'])].groupby('TripID').ts.min()
_a=e[e.EventName=='Travel Request Approved'].groupby('TripID').size()
t['book']=t.TripID.map(_b);t['dep']=t.TripID.map(_d);t['appr']=(t.TripID.map(_a).fillna(0)>0).astype(int)
t['bl']=(t.dep-t.book).dt.total_seconds()/86400
MONTHS=[f'2023-12']+[f'2024-{m:02d}' for m in range(1,13)]+['2025']
mk=t.book.dt.strftime('%Y-%m'); t['mo']=mk.map(lambda x: MONTHS.index(x) if x in MONTHS else 13)
lbk=np.select([t.bl.isna(),t.bl<3,t.bl<7,t.bl<14],[4,0,1,2],3)
for i in range(5):
    t[f'lb{i}']=(lbk==i).astype(int); t[f'lo{i}']=((lbk==i)&(t.OutOfPolicy=='Yes')).astype(int)
t['oopAppr']=((t.OutOfPolicy=='Yes')&(t.appr==1)).astype(int)
NM=len(MONTHS)
t['cell']=(((t.ri*len(BU)+t.bi)*len(P)+t.pi)*2+t.lh)*NM+t.mo
M=['trips','tot','tkg','hkg','spend','oop','flegs','prem','premkg','fkg','upl','lhlegs','lhkg','corrlegs','corrkg','trains','b1','b2','b3','k1','k2','k3','internal','intkg','intflown','nonfkg','cabdol',
   'nmE','nmB','nmF','nmT','nmC','oopE','oopB','oopF','oopT','oopC','nochgkg','s2','s2kg','s0','intlh','lhint_kg','appr','oopAppr','lb0','lb1','lb2','lb3','lb4','lo0','lo1','lo2','lo3','lo4']
t['trips']=1; t['spend']=t.NetCosts; t['intkg']=t.tot*t.internal; t['intflown']=((t.internal==1)&(t.flegs>0)).astype(int)
for k,c in zip('EBFTC',['Economy','Business','First','Train','Car']):
    t['nm'+k]=(t.nm2==c).astype(int); t['oop'+k]=((t.nm2==c)&(t.oop==1)).astype(int)
t['nochgkg']=np.where(t.nm2=='',t.tot,0); t['s2']=(t.score>=2).astype(int); t['s2kg']=t.tot*t.s2; t['s0']=(t.score==0).astype(int)
t['intlh']=t.internal*t.lh; t['lhint_kg']=t.tot*t.internal*t.lh
cube=t.groupby('cell')[M].sum()
cells={int(c):[round(float(v),1) for v in row] for c,row in cube.iterrows()}
# routes
RT=list(t.route.value_counts().index); t['rti']=t.route.map(RT.index)
rc=t.groupby(['cell','rti']).agg(n=('trips','sum'),kg=('tot','sum'),ni=('internal','sum')).reset_index()
routes=[[int(r.cell),int(r.rti),int(r.n),round(r.kg/1000,2),int(r.ni)] for r in rc.itertuples()]

routes=[[int(r.cell),int(r.rti),int(r.n),round(r.kg/1000,2),int(r.ni)] for r in rc.itertuples()]
rmeta=[]
for r in RT:
    d,ar=r.split(' → '); row=t[t.route==r].iloc[0]
    rmeta.append([r,round(hv(d,ar)),row.ArrivalLocationCountry])
# corridor segments by cell
cl=l[l['corr']].merge(t[['TripID','cell']],on='TripID')
CS=corr
cc=cl.groupby(['cell','seg']).agg(f=('flight','sum'),n=('flight','size')).reset_index()
corridors=[[int(r.cell),CS.index(r.seg),int(r.f),int(r.n-r.f)] for r in cc.itertuples()]
cmeta=[[s,round(float(trainseg[s]))] for s in CS]
# policy segments: flights by cell x seg x cabin
fl2=fl.merge(t[['TripID','cell']],on='TripID')
SG=sorted(fl2.seg.unique())
ps=fl2.groupby(['cell','seg','cabin']).agg(n=('kg','size'),kg=('kg','sum'),ek=('econkg','sum'),tk=('trainkg','sum'),cd=('cdiff','sum')).reset_index()
pseg=[[int(r.cell),SG.index(r.seg),'EBF'.index(r.cabin),int(r.n),round(r.kg/1000,3),round(r.ek/1000,3),round(r.tk/1000,3),round(r.cd)] for r in ps.itertuples()]
smeta=[[s,round(float(fl[fl.seg==s].km.iloc[0])),s in CS] for s in SG]
# breach list: top trips by tot with score>=2
bl=t[t.score>=2].sort_values(['score','tot'],ascending=[False,False]).head(400)
breach=[[int(r.TripID),int(r.cell),int(r.score),round(r.tot/1000,2),int(r.oop)] for r in bl.itertuples()]
# variants
pc=t.groupby('pcode').agg(all=('trips','sum'),chg=('nm2',lambda x:(x!='').sum()),up=('nm2',lambda x:x.isin(['Business','First']).sum()))
variants=[[k,int(r['all']),int(r.chg),int(r.up)] for k,r in pc.iterrows()]
l[['TripID','kg','ShippingTypeDescription']].to_pickle(os.path.join(TMP,'legsx.pkl'));t[['TripID','book','dep','bl','appr','mo','cell','tot','hkg','nm2','OutOfPolicy','ri','bi','pi','lh']].to_pickle(os.path.join(TMP,'tripx.pkl'))
out=dict(MONTHS=MONTHS,NM=NM,R=R,BU=BU,P=P,M=M,cells=cells,RT=rmeta,routes=routes,CS=cmeta,corridors=corridors,SG=smeta,pseg=pseg,breach=breach,variants=variants)
json.dump(out,open(os.path.join(OUT,'data.json'),'w'),separators=(',',':'))
import os;print('size KB',os.path.getsize(os.path.join(OUT,'data.json'))//1024, 'cells',len(cells),'pseg',len(pseg),'routes',len(routes))
# validation prints
print('corridors',CS); print('corr flights',l[l['corr']&l.flight].shape[0],'trains',l[l['corr']&~l.flight&(l.ShippingTypeDescription=="Train")].shape[0])
bu=t.groupby('BusinessUnit').agg(tr=('trips','sum'),lh=('lh','sum'),lhkg=('tot',lambda x:x[t.loc[x.index,'lh']==1].sum()/1000),tot=('tot','sum'))
print(bu.head(6)); print('s2',t.s2.sum(),t.s2kg.sum()/t.tot.sum(),'s0',t.s0.sum())
up=t[t.nm2.isin(['Business','First'])]; print('upgrades',len(up),'oop',up.oop.mean())
for c in ['Business','First','Economy','Train','Car']: print(c,(t.nm2==c).sum(),t[t.nm2==c].oop.mean())
print('nochg share',t.nochgkg.sum()/t.tot.sum(),'internal kg share',t.intkg.sum()/t.tot.sum())
print('internal LH share',t[t.internal==1].lh.mean())
