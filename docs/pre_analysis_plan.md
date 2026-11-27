# Pre-analysis plan

_Written 23 November 2026, before the district outcome data or night-light
exports were downloaded. Changes after that date are listed at the bottom with
reasons._

## 1. Question

Did districts with more power outages during the 2026 measles-rubella (MR)
campaign see relatively more measles cases after vaccine protection should have
begun?

## 2. Mechanism

MR vaccine must be kept at 2-8 deg C, and reconstituted vaccine is especially
sensitive to heat. Power cuts at upazila health complexes, combined with
heat-wave temperatures, could reduce vaccine potency. Children would then be
counted as vaccinated without being protected. If this happened, the result
would look like this: high-outage districts show *relatively* more cases after
the campaign than low-outage districts, beyond what their pre-campaign trends
and susceptible depletion predict.

## 3. Hypotheses

* **H1 (primary):** In the main model, the post x campaign-window-outage rate
  ratio is > 1.
* **H2:** The effect is larger for "hot outage" nights (deep outage and Tmax
  > 35 C) than for outage alone.
* **H3 (falsification):** Outage *before* the campaign (1 March - 19 April),
  entered in the same model, has a rate ratio of about 1.

H1 together with H3 supports the cold-chain reading. If H1 holds and H3 fails,
the association more likely reflects general rural disadvantage.

## 4. Data

| Variable | Source | Level |
|---|---|---|
| Suspected / confirmed cases, deaths | DGHS measles platform API | district-day |
| Outage proxy | NASA Black Marble VNP46A2, observed (not gap-filled) radiance, quality flags 0-1 | district-night |
| Temperature | ERA5-Land daily max 2 m | district-day |
| Load shedding | BPDB/NLDC daily report, zone table | 9 zones-day |
| Population, under-5 | BBS census 2022 | district |

## 5. Definitions (fixed in `src/ccd/config.py`)

* Study weeks: 13 April - 27 September 2026 (Monday-start).
* Campaign window: 20 April - 31 May 2026. **The end date is to be verified
  against DGHS releases before the main run.** If it differs, the verified date
  will be used and the change logged below.
* Post period: from campaign end + 3 weeks.
* Outage index: mean over usable nights of `1 - min(1, radiance / Dec-Feb median)`
  on normally-lit pixels (baseline > 2 nW/cm2/sr).
* Usable night: at least 30% of lit pixels cloud-free and high quality.
* Deep-outage night: ratio < 0.70. Hot day: Tmax > 35 C.

## 6. Primary model

Poisson QMLE with district and week fixed effects, offset log(under-5
population), and exposure z-scored across districts:

    cases_dw ~ a_d + g_w + b*(post_w x outage_d) + c*(post_w x pre_attack_d)

Standard errors are clustered by district (64 clusters). The estimate reported
is exp(b) with a 95% CI.

## 7. Secondary and robustness analyses (all pre-specified)

1. Event study: exposure x relative-week dummies (reference: week -1).
2. Placebo: pre-campaign outage as the exposure.
3. Horse race: campaign and pre-campaign outage in one model.
4. Deep-outage and hot-outage exposures.
5. Negative binomial (NB2) with alpha estimated from FE-Poisson residuals.
6. Exposure from BPDB zone load-shed share (coarse, 9 zones).
7. Outcome: lab-confirmed cases.
8. Proxy validation: Spearman correlation between the zone-averaged
   night-light index and BPDB zone load-shed share on the same days.

## 8. Threats and how they are handled

| Threat | Handling |
|---|---|
| Rural disadvantage confounds outage and cases | District FE; placebo; horse race |
| Susceptible depletion (early-hit districts run out of susceptibles) | post x pre-campaign attack rate |
| Reporting differences between districts | District FE; confirmed-case check |
| Clouds bias the night-light series | Quality filter; usable-night counts reported |
| Overpass time (01:30) misses evening cuts | BPDB zone data as second exposure |
| Short pre-period (platform from 10 April) | Stated plainly; event study shows what exists |
| Generators or solar fridges at facilities | Would bias toward null; stated |

## 9. What would count as a null result

If the 95% CI of the main estimate includes 1, we report that there is **no
detectable association**. A null result is still informative: it suggests the
outbreak's persistence after April is better explained by coverage gaps than by
cold-chain failure.

## Change log

* **24 November 2026: added a historical parallel-trends check** (`scripts/06_historical_pretrends.py`).
  The reason was a discussion with Prof. Enrico Rettore (University of Padova), who pointed out that the
  design identifies the differential effect of the campaign only under parallel trends. The 2026
  pre-period is about ten days long, so the check uses annual district counts for 2017-2023:
  `cases_dy ~ district FE + year FE + exposure_d x (year - mean)`, Poisson, SE clustered by district,
  plus an exposure x year event study. This was added before any 2026 district outcome data were
  downloaded. The first run used the BPDB zone burden ratio as a proxy exposure; the final run will
  use the campaign-window night-light exposure.
* **27 November 2026: added an alternative estimate with district-specific linear trends**
  (`models.did(..., district_trends=True)`), on Prof. Rettore's advice: report the conservative main
  estimate and, as an alternative, one that allows each district its own linear trend. Added before
  any 2026 district outcome data were downloaded.
