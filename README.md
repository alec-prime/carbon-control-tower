# Carbon Control Tower

A standalone web application, styled after the Celonis platform, for decarbonizing corporate business travel toward Net Zero 2030. It rebuilds an MSBA capstone's Celonis Studio dashboards as a single self-contained page, including a process explorer and a variant explorer built from the trip event log.

**Run it:** open `index.html` in a browser. The page needs no server and no build step: data, charts and map are inlined. Only the Inter font loads from Google Fonts.

> Data is fictional and was provided by Celonis for educational use. Nothing here represents Celonis's actual travel policy or footprint.

## The story

The app makes one argument: travel carbon is concentrated in a few booking choices that the current process never checks, and four policies enforced at booking can cut about half of it on the path to Net Zero 2030.

| # | Dashboard | Question | How it answers |
|---|---|---|---|
| 1 | Emissions Overview | Where is the carbon, and who generates it? | Long haul is 64% of flights but about 90% of flight carbon. The By region tab shows Asia Pacific generating two-thirds of tCO2e because its routes are long haul. The map shows tCO2e by destination country. |
| 2 | Key Carbon KPIs | How big is each problem today? | Four problems on one 0–100% scale: premium cabins, internal meetings held in person, flights where rail runs, and long haul by business unit. |
| 3 | Policy Impact | What would each policy save? | Six controls drive four levers applied in order (rail → economy → virtual → long-haul budget), so the levers add up exactly to the total cut. Shows dollars, results by unit and region, and the 2030 glide path. |
| 4 | Process Controls | Do bookings follow policy, and who breaks it? | Mode, cabin and route are fixed at Book Mode of Transportation, and approval never checks carbon. 96.4% of breaching trips are still approved. Includes a process explorer and variant explorer, breach rates by region and business unit, a breach queue, and the proposed controls. |
| 5 | Data Trust | Can we believe the numbers? | Trip and event totals reconcile, the lever identity holds at any setting, and a great-circle recount reproduces 60,390 long-haul flights and 51,873 long-haul trips. |

Region, Business unit, Purpose and Booking month filters apply across every view. The process and variant explorers always show all trips.

## Repository layout

```
index.html                 Built app (open this)
src/app.html               App template: UI, charts, policy engine
src/process-explorer.js    Process explorer component
src/world-map.json         Pre-projected country paths for the map
data/derived/data.json     Filterable data cube (region × BU × purpose × long-haul × booking month)
data/derived/pe.json       Process graph, variants and event-level CO2e from the event log
data/raw/                  Source CSVs (not committed; see below)
pipeline/                  Python and Node scripts that rebuild everything above
```

## Rebuilding from source data

1. Put the four capstone CSVs in `data/raw/`:
   - `Trip_Data_No_Emissions.csv`
   - `Transportations_Data_No_Emissions.csv`
   - `Trip_Event_Attributes.csv`
   - `Trip_Event_Log.csv`
2. Run:

```bash
pip install -r requirements.txt
python pipeline/emissions_model.py   # leg distances and emissions; parses the event log
python pipeline/aggregate.py         # calibrates and writes data/derived/data.json
python pipeline/process_log.py       # writes data/derived/pe.json
python pipeline/assemble.py          # inlines everything into index.html
```

`pipeline/world_map.js` regenerates `src/world-map.json`. You only need it to change the map projection: `cd pipeline && npm install && node world_map.js`.

## How the carbon figures are built

The source files carry no emissions, so leg tCO2e is distance-based:

- **Flights:** great-circle km between the booked cities × a BEIS-style factor by haul band (domestic, short haul, long haul over 3,700 km) and cabin. The factor includes radiative forcing and an 8% routing uplift, and is doubled for the return leg.
- **Trains and cars:** per-km factors.
- **Hotels:** allocated by nights.

Totals are then calibrated to the project's Climatiq pipeline:
- region totals match the pipeline's regional scorecard;
- premium-cabin uplift is 76,976 t;
- cabin dollars are $72.5M;
- total is 232,981 tCO2e.

Uncalibrated cross-checks land within about 1%: premium share of flight emissions is 53.4% (pipeline 53.3%), and long-haul trip share of tCO2e is 90.2% (pipeline 90.5%).

Event-level carbon puts departure and return carbon on the travel events and hotel carbon on Book Lodging. Carbon with no matching travel event goes on Book Mode of Transportation ("held at booking": 16.5%, pipeline 16.0%).

To use the pipeline's exact figures, replace the model with the `CASES` and `LEG_EMISSIONS` tables from the Celonis data pool.

## Known data findings

- **Corridor flight legs:** 7,078, not the 5,755 shown in one earlier mockup. 7,078 also reproduces the 24.3% rail share on corridors.
- **Berlin–Madrid:** 336 train legs at about 1,870 km, so it falls outside the 1,200 km corridor threshold. Data Trust flags it.
- **Booking lead time:** measured from first booking to first departure, no trip booked 14 or more days ahead breaks the rule. 44.8% of breaches are booked under 3 days ahead, 20.7% at 3–6 days and 30.9% at 7–13 days.
