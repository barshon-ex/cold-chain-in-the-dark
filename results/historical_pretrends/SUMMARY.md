# Historical parallel-trends check

Exposure: BPDB zone load-shedding burden ratio, Sep-Nov 2026 (PROXY: nine zones, outside the campaign window; rerun after steps 3-4).
Data: annual confirmed measles cases, 64 districts with any cases, 2017-2023 (source: github.com/abubokkorshiddik/District-Level-Measles-Outbreak-Bangladesh, commit cf393b8; case-count provenance not documented there).

- Differential trend: rate ratio **0.911 per year** per +1 SD exposure (95% CI 0.827-1.003, p = 0.06) -> borderline evidence of a differential pre-2026 trend: treat as a warning, not a pass.
- Direction: higher-exposure districts were trending DOWN relative to the others, so if that trend continued, the 2026 DiD is biased towards finding FEWER post-campaign cases there, i.e. against the cold-chain hypothesis; a main estimate above 1 would then be conservative.
- Event study (exposure x year, reference = last year):

| year | rate ratio | 95% CI |
|---|---|---|
| 2017 | 1.92 | 0.96-3.85 |
| 2018 | 1.24 | 0.76-2.01 |
| 2019 | 1.21 | 0.69-2.12 |
| 2020 | 1.48 | 0.84-2.59 |
| 2021 | 0.99 | 0.68-1.44 |
| 2022 | 0.89 | 0.64-1.24 |
| 2023 | 1.00 | 1.00-1.00 |

Caveats: annual data, not weekly; 2020-21 reporting was disrupted by COVID-19; with the zone proxy, exposure varies across only nine zones, so district-clustered standard errors are optimistic. A null here supports, but does not prove, parallel trends in 2026.
