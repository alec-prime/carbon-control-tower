# Carbon Control Tower

A standalone web application, styled after the Celonis platform, for decarbonizing corporate business travel toward Net Zero 2030. It rebuilds an MSBA capstone's Celonis Studio dashboards as a single self-contained page, including a process explorer and a variant explorer built from the trip event log.

**Live app:** https://alec-prime.github.io/carbon-control-tower/

**Run it locally:** open `index.html` in a browser. The page needs no server and no build step: data, charts and map are inlined. Only the Inter font loads from Google Fonts.

> Data is fictional and was provided by Celonis for educational use. Nothing here represents Celonis's actual travel policy or footprint.

## The story

The app makes one argument: travel carbon is concentrated in a few booking choices that the current process never checks, and four policies enforced at booking can cut about half of it on the path to Net Zero 2030.

| # | Dashboard | Question | How it answers |
|---|---|---|---|
| 1 | Emissions Overview | Where is the carbon, and who generates it? | Long haul is 64% of flights but about 91% of flight carbon. The By region tab shows Asia Pacific generating two-thirds of tCO2e because its routes are long haul. The map shows tCO2e by destination country. |
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
data/derived/data.json     Filterable data cube (region × BU × purpose × long-haul × booking month) plus the facts Data Trust quotes
data/derived/pe.json       Process graph, variants and event-level CO2e from the event log
data/raw/                  Source CSVs (not committed; see below)
pipeline/                  Python and Node scripts that rebuild everything above
```

## Rebuilding from source data

The app reads the data pool tables directly. Nothing is modelled or calibrated.

1. Put the five tables in `data/raw/`:
   - `CASES.csv`: one row per trip (87,053), with carbon, cost, lead time and process attributes
   - `LEGS.csv`: one row per transport leg (99,925), with `Leg_CO2e` and the per-leg alternatives `Alt_Economy_Leg_CO2e` and `Alt_Rail_Leg_CO2e`
   - `ACTIVITIES.csv`: the event log (895,366 events), with `Event_CO2e` and `CO2eAllocation`
   - `DIM_CITY.csv`: city coordinates and countries
   - `DIM_MODE.csv`: mode family, cabin tier, fuel type and premium flag
2. Run:

```bash
pip install -r requirements.txt
python pipeline/load_data.py      # loads and reconciles the five tables
python pipeline/aggregate.py      # writes data/derived/data.json
python pipeline/process_log.py    # writes data/derived/pe.json
python pipeline/assemble.py       # inlines everything into index.html
```

`pipeline/world_map.js` regenerates `src/world-map.json`. You only need it to change the map projection: `cd pipeline && npm install && node world_map.js`.

## Where the carbon figures come from

Every tCO2e figure is a value in the source tables. The totals are 232,981 t: 226,485 t transport (`LEGS.Leg_CO2e`, departure plus return) and 6,496 t hotels (`CASES.Hotel_CO2e`).

- **Policy savings** use the pipeline's own alternatives on each leg. Cabin saving is `Leg_CO2e − Alt_Economy_Leg_CO2e` (76,976 t, equal to `CASES.CabinCapSaving_CO2e`); rail saving is `Leg_CO2e − Alt_Rail_Leg_CO2e` on corridor flights.
- **Cabin dollars** are premium leg cost × (1 − 1 / 2.5), directional: $72,533,278. The 2.5 is the Celonis `premium_fare_multiple`, set in `pipeline/common.py`.
- **Event carbon** is `ACTIVITIES.Event_CO2e`. Departure and return carbon sit on the travel events, hotel carbon on Book Lodging, and carbon with no matching travel event is "Held at booking" (37,264 t, 16.0%, on 33,428 trips).
- **Long haul** is a flight over 3,700 km by `distance_km`: 60,390 legs on 51,873 trips. A great-circle recount from `DIM_CITY` gives the same counts.
- **Lead time** is measured on the booking clock, from the first Book Mode of Transportation to the first departure, taken from `ACTIVITIES`. `CASES.LeadTimeDays` uses the confirmation clock instead, which is why its breach median is 0.02 days.

`load_data.py` checks the tables against each other before anything is built: legs, hotels, events and trips tie out to the kilogram, every leg's mode matches `DIM_MODE`, and every city has coordinates and a matching country in `DIM_CITY`. The Data Trust view shows the same checks.

## Known data findings

- **Corridor flight legs:** 7,078 on 10 corridors, where a corridor is a route with a train booking and a flight distance under 1,200 km. Rail carries 24.3% of corridor legs (2,268 train legs).
- **Berlin–Madrid:** 336 train legs at about 1,851 km flight distance, so it falls outside the 1,200 km corridor threshold. Data Trust flags it.
- **Sydney–Perth by train:** 3 legs flagged `IsAnomalousRoute`; they sit outside the corridor list.
- **Booking lead time:** measured from first booking to first departure, no trip booked 14 or more days ahead breaks the rule. 44.8% of breaches are booked under 3 days ahead, 20.7% at 3–6 days and 30.9% at 7–13 days.
- **Approval:** 96.4% of breaching trips are still approved.
