// Regenerates src/world-map.json: Mercator SVG paths for every country (Antarctica excluded),
// keyed by ISO alpha-2 so the app can colour countries by arrival tCO2e.
// Usage: cd pipeline && npm install && node world_map.js
const topo=require('world-atlas/countries-110m.json');
const {feature}=require('topojson-client');
const d3=require('d3-geo');
const iso=require('i18n-iso-countries');
const path=require('path');
const fc=feature(topo,topo.objects.countries);
fc.features=fc.features.filter(f=>f.properties.name!=='Antarctica');
const W=1000,H=620;
const proj=d3.geoMercator().rotate([-10,0]).fitExtent([[10,10],[W-10,H-10]],{type:'MultiPoint',coordinates:[[-169.9,-56],[189.9,-56],[189.9,80],[-169.9,80]]});
const gp=d3.geoPath(proj).digits(1);
const out=fc.features.map(f=>({n:f.properties.name,a:iso.numericToAlpha2(f.id)||'',d:gp(f)})).filter(x=>x.d);
require('fs').writeFileSync(path.join(__dirname,'..','src','world-map.json'),JSON.stringify(out));
console.log('countries',out.length);
