const PEX=__PEX__;
const MAINSEQ=['Book Mode of Transportation','Book Lodging','Submit Travel Request','Travel Request Approved','Receive Confirmation','Take Departure Flight','Take Return Flight','Submit Expense Request','Expense Request Approved','Expense Reimbursement'];
function processExplorer(box){
  const A=PEX.ACT.map((a,i)=>({i,name:a[0],ev:a[1],cs:a[2],co2:a[3],main:MAINSEQ.includes(a[0])}));
  const S={i:-1,name:'Start',ev:87053,cs:87053,co2:0,main:true,se:true},E={i:-2,name:'End',ev:87053,cs:87053,co2:0,main:true,se:true};
  const byI=i=>i===-1?S:i===-2?E:A[i];
  const ED=PEX.EDGES.map(e=>({f:e[0],t:e[1],n:e[2],h:e[3]}));
  const maxCo2=Math.max(...A.map(a=>a.co2));
  box.innerHTML=`<div class="tl"><div class="tb" title="Activities shown"><svg width="14" height="10"><path d="M1 5h12M4 1v8M10 1v8" stroke="#0F1F42" fill="none"/></svg><b id="nAct"></b></div>
    <div class="tb"><select id="kpiSel"><option value="freq">Case frequency</option><option value="co2">Event tCO2e</option><option value="time">Median time between steps</option></select></div>
    <div class="tb" id="playBtn" title="Animate case flow">▶</div></div>
    <div class="tr"><div class="vslide"><div class="lab">Activities</div><input type="range" id="actS" min="10" max="${A.length}" value="12"><div class="num" id="actN"></div></div>
    <div class="vslide"><div class="lab">Connections</div><input type="range" id="conS" min="5" max="100" value="40"><div class="num" id="conN"></div></div></div>
    <div class="br"><div class="tb" id="legBtn">☰ Legend</div><div class="tb"><span id="fitB" title="Fit">⤢</span><span id="zo">−</span><span id="zl" style="min-width:34px;text-align:center">100%</span><span id="zi">+</span></div></div>
    <div class="legend" id="leg"><b>Process Explorer</b><br><span class="sw" style="border-top:4px solid var(--teal)"></span>Directly-follows connection, width ∝ cases<br><span class="sw" style="border-top:2px dashed var(--teal)"></span>Start / end<br><span class="sw" style="border-top:2px solid #C9CCD8"></span>Rework or backward step<br><span id="co2leg" style="display:none"><span class="sw" style="display:inline-block;height:10px;background:linear-gradient(90deg,#FFF1EC,#F26A4B,#8A1F07)"></span>Event tCO2e (heat)</span><br>Source: Trip_Event_Log, ${fmt(PEX.ACT.reduce((a,b)=>a+b[1],0))} events, all trips.</div>
    <div class="detail" id="det"><span class="x" id="detx">✕</span><div id="detb"></div></div>
    <svg class="canvas" id="pesvg"><defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1E9C9C"/></marker><marker id="arrg" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#B5B9C8"/></marker></defs><g id="peg"></g></svg>`;
  const svg=$('#pesvg'),g=$('#peg');
  const st={nAct:12,con:40,kpi:'freq',k:.6,tx:0,ty:0,play:false,sel:null};
  const NW=200,NH=40,GAP=64,LW=170;
  // static layout: main rows, then place others near their dominant main neighbours
  const row={};row[-1]=0;MAINSEQ.forEach((n,k)=>{row[A.find(a=>a.name===n).i]=k+1});row[-2]=MAINSEQ.length+1;
  const domNb=(i,dir)=>{const c=ED.filter(e=>dir==='in'?e.t===i:e.f===i).map(e=>({o:dir==='in'?e.f:e.t,n:e.n})).filter(x=>row[x.o]!=null).sort((a,b)=>b.n-a.n);return c.length?row[c[0].o]:null};
  const others=A.filter(a=>!a.main).sort((a,b)=>b.ev-a.ev);
  others.forEach(a=>{const p=domNb(a.i,'in'),s=domNb(a.i,'out');row[a.i]=p!=null&&s!=null?(p<s?(p+s)/2:p+.5):(p!=null?p+.5:s!=null?s-.5:5)});
  const lanes={};const lane={};others.forEach(a=>{const key=Math.round(row[a.i]*2)/2;const k=(lanes[key]=(lanes[key]||0)+1);lane[a.i]=k%2?Math.ceil(k/2):-Math.ceil(k/2)});
  function layout(vis){const pos={};const exp=[...vis].some(i=>!byI(i).main);const sc=exp?1.6:1;
    [...vis].forEach(i=>{const a=byI(i);const y=row[i]*GAP*sc;if(a.main){pos[i]={x:a.se?(NW-110)/2:0,y,w:a.se?110:NW}}else{const l=lane[i];pos[i]={x:l>0?NW+50+(l-1)*(LW+28):-50-LW-(-l-1)*(LW+28),y,w:LW}}});return pos}
  const heat=v=>{const t=Math.sqrt(v/maxCo2);const a=[255,241,236],b=[242,106,75],c=[138,31,7];const m=(p,q,s)=>p.map((x,i)=>Math.round(x+(q[i]-x)*s));return `rgb(${t<.5?m(a,b,t*2):m(b,c,(t-.5)*2)})`};
  const hfmt=h=>h>=48?(h/24).toFixed(1)+' d':h>=1?h.toFixed(1)+' h':Math.round(h*60)+' min';
  function wrap(s,n){const w=s.split(' ');const out=[''];w.forEach(x=>{if((out[out.length-1]+' '+x).trim().length>n)out.push(x);else out[out.length-1]=(out[out.length-1]+' '+x).trim()});return out.slice(0,2)}
  function draw(){
    g.innerHTML='';const ranked=[...A].sort((a,b)=>b.ev-a.ev);const vis=new Set([-1,-2,...ranked.slice(0,st.nAct).map(a=>a.i)]);
    // main activities always visible
    A.filter(a=>a.main).forEach(a=>vis.add(a.i));
    const pos=layout(vis);
    const shown=ED.filter(e=>vis.has(e.f)&&vis.has(e.t)).sort((a,b)=>b.n-a.n);const keep=shown.slice(0,Math.max(12,Math.ceil(shown.length*st.con/100)));
    const maxE=Math.max(...keep.map(e=>e.n));const eg=el('g',{},g),lg=el('g',{},g),ng=el('g',{},g);const paths=[];
    keep.forEach(e=>{const P=pos[e.f],Q=pos[e.t];if(!P||!Q)return;let d;const back=Q.y<=P.y;const pcx=P.x+P.w/2,qcx=Q.x+Q.w/2;
      if(back){const ox=Math.max(P.x+P.w,Q.x+Q.w)+24+(e.n%7)*4;d=`M${P.x+P.w},${P.y+NH/2}C${ox},${P.y+NH/2} ${ox},${Q.y+NH/2} ${Q.x+Q.w+2},${Q.y+NH/2}`}
      else if(Math.abs(pcx-qcx)<2){d=`M${pcx},${P.y+NH}L${qcx},${Q.y-2}`}
      else{const my=(P.y+NH+Q.y)/2;d=`M${pcx},${P.y+NH}C${pcx},${my} ${qcx},${my} ${qcx},${Q.y-2}`}
      const w=1+9*Math.sqrt(e.n/maxE);const se=e.f<0||e.t<0;
      const pth=el('path',{d,fill:'none',stroke:back?'#B5B9C8':'#1E9C9C','stroke-width':back?Math.max(1,w*.6):w,'stroke-opacity':.85,'stroke-dasharray':se?'2 2':'','marker-end':back?'url(#arrg)':'url(#arr)'},eg);
      bindTip(pth,`<b>${byI(e.f).name} → ${byI(e.t).name}</b><br>${fmt(e.n)} cases${e.h?'<br>Median '+hfmt(e.h):''}`);paths.push([pth,e.n]);
      if(e.n>=maxE*.02){const L=pth.getTotalLength();const pt=pth.getPointAtLength(L*.5);const txt=st.kpi==='time'&&e.h?hfmt(e.h):fk(e.n);const lw=txt.length*5.6+18;
        const lgp=el('g',{class:'elab',transform:`translate(${pt.x+4},${pt.y-8})`},lg);el('rect',{width:lw,height:16,rx:3},lgp);
        el(st.kpi==='time'?'circle':'rect',st.kpi==='time'?{cx:7,cy:8,r:3.5,fill:'none',stroke:'#4B5772','stroke-width':.8}:{x:3,y:4,width:8,height:8,rx:1,fill:'none',stroke:'#4B5772','stroke-width':.8},lgp);const tt=el('text',{x:14,y:11.5},lgp);tt.textContent=txt}});
    [...vis].forEach(i=>{const a=byI(i),P=pos[i];if(!P)return;const n=el('g',{class:'node'+(st.sel===i?' sel':''),transform:`translate(${P.x},${P.y})`},ng);
      const lines=wrap(a.name,P.w>180?30:24);el('rect',{width:P.w,height:lines.length>1?NH+4:NH,rx:a.se?20:5},n);
      el('circle',{cx:16,cy:NH/2,r:7,fill:st.kpi==='co2'?(a.co2?heat(a.co2):'#E7E8EE'):a.main?'#1E9C9C':'#7FC6C6'},n);
      lines.forEach((ln,k)=>{const t=el('text',{x:30,y:14+k*11,class:'t'},n);t.textContent=ln});
      const cv=el('text',{x:30,y:lines.length>1?36:28,class:'c'},n);cv.textContent=st.kpi==='co2'?fmt(a.co2)+' tCO2e':'# '+fk(a.ev);
      n.addEventListener('click',ev=>{ev.stopPropagation();st.sel=i;detail(a);draw()});
      bindTip(n,`<b>${a.name}</b><br>${fmt(a.ev)} events · ${fmt(a.cs)} trips${a.co2?'<br>'+fmt(a.co2)+' event tCO2e':''}`)});
    if(st.play)paths.forEach(([p,c])=>{const k=Math.max(1,Math.round(4*c/maxE));for(let j=0;j<k;j++){const dot=el('circle',{r:3,fill:'#0F1F42'},eg);el('animateMotion',{dur:'3s',repeatCount:'indefinite',begin:(j*3/k)+'s',path:p.getAttribute('d')},dot)}});
    $('#nAct').textContent=vis.size-2;$('#actN').textContent=st.nAct;$('#conN').textContent=st.con+'%';$('#co2leg').style.display=st.kpi==='co2'?'inline':'none';apply();
  }
  function detail(a){const ins=ED.filter(e=>e.t===a.i).sort((x,y)=>y.n-x.n).slice(0,4),outs=ED.filter(e=>e.f===a.i).sort((x,y)=>y.n-x.n).slice(0,4);
    $('#detb').innerHTML=`<h4>${a.name}</h4><div class="rows"><div class="row"><span>Events</span><b>${fmt(a.ev)}</b></div><div class="row"><span>Trips</span><b>${fmt(a.cs)} (${(a.cs/870.53).toFixed(1)}%)</b></div><div class="row"><span>Event tCO2e</span><b>${fmt(a.co2)}</b></div></div>
      <div class="note" style="margin-top:8px"><b>From:</b> ${ins.map(e=>`${byI(e.f).name} (${fk(e.n)})`).join(', ')||'—'}<br><b>To:</b> ${outs.map(e=>`${byI(e.t).name} (${fk(e.n)}${e.h?', '+hfmt(e.h):''})`).join(', ')||'—'}</div>`;$('#det').classList.add('show')}
  $('#detx').onclick=e=>{e.stopPropagation();$('#det').classList.remove('show');st.sel=null;draw()};
  function apply(){g.setAttribute('transform',`translate(${st.tx},${st.ty}) scale(${st.k})`);$('#zl').textContent=Math.round(st.k*100)+'%'}
  function fit(){const bb=g.getBBox();const W=svg.clientWidth,H=svg.clientHeight;st.k=Math.min((W-150)/bb.width,(H-110)/bb.height,1.2);st.tx=(W-90-bb.width*st.k)/2-bb.x*st.k;st.ty=58-bb.y*st.k;apply()}
  $('#actS').oninput=e=>{st.nAct=+e.target.value;draw();fit()};$('#conS').oninput=e=>{st.con=+e.target.value;draw()};
  $('#kpiSel').onchange=e=>{st.kpi=e.target.value;draw()};
  $('#playBtn').onclick=()=>{st.play=!st.play;$('#playBtn').textContent=st.play?'❚❚':'▶';$('#playBtn').classList.toggle('on',st.play);draw()};
  $('#legBtn').onclick=()=>$('#leg').classList.toggle('show');
  const zoom=f=>{const W=svg.clientWidth/2,H=svg.clientHeight/2;const nk=Math.max(.15,Math.min(2.5,st.k*f));st.tx=W-(W-st.tx)*nk/st.k;st.ty=H-(H-st.ty)*nk/st.k;st.k=nk;apply()};
  $('#zi').onclick=()=>zoom(1.2);$('#zo').onclick=()=>zoom(1/1.2);$('#fitB').onclick=fit;
  svg.addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY<0?1.1:1/1.1)},{passive:false});
  let dr=null;svg.addEventListener('mousedown',e=>{dr={x:e.clientX,y:e.clientY,tx:st.tx,ty:st.ty};svg.classList.add('drag')});
  addEventListener('mouseup',()=>{dr=null;svg.classList.remove('drag')});
  svg.addEventListener('mousemove',e=>{if(!dr)return;st.tx=dr.tx+e.clientX-dr.x;st.ty=dr.ty+e.clientY-dr.y;apply()});
  draw();requestAnimationFrame(fit);
}
