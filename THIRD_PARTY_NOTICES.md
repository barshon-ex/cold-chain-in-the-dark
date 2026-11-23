# Third-party code and data

| What | From | License | How used |
|---|---|---|---|
| `src/ccd/bpdb_parser.py` | [sunrisesineast/bangladesh-grid](https://github.com/sunrisesineast/bangladesh-grid), `scripts/nldc.py` | MIT, (c) 2026 bangladesh-grid contributors | Parsing functions vendored, network code removed |
| `data/external/bpdb_zone_evening_peak_2026-09-04_2026-11-21.csv` | same repository, `data/nldc-daily.json`, parsed from BPDB/NLDC daily reports | MIT (compilation); underlying reports by BPDB | Reshaped to one row per zone-day |
| `data/external/population_adm2_2022.csv`, `admin_lookup.csv` | [kathsherratt/measles-bgd](https://github.com/kathsherratt/measles-bgd), `data/covariates/` (BBS Population and Housing Census 2022) | MIT, (c) 2026 Kath Sherratt | Copied unchanged |
| DGHS platform API usage (endpoint, parameters, known quirks) | kathsherratt/measles-bgd, `R/data/01-fetch-dashboard.R` | MIT | Re-implemented in Python in `src/ccd/dghs.py` |

Data fetched by the scripts at run time (not redistributed here):
DGHS measles platform (measles.dghs.gov.bd); BPDB daily-generation archive
(misc.bpdb.gov.bd); NASA Black Marble VNP46A2 and ECMWF ERA5-Land via Google
Earth Engine; geoBoundaries v6 ADM2 (CC BY 4.0).

The MIT license text of each source is in the source repository and applies to
the vendored or copied parts listed above.
