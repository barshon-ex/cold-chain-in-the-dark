# Results (SYNTHETIC DEMO)

_Generated 2026-11-23 11:05. SYNTHETIC DATA - pipeline demo, not a finding (planted rate ratio 1.25)_

- Panel: 64 districts x 24 weeks (13 Apr to 21 Sep 2026), 455,764 suspected cases.
- Main estimate: rate ratio **1.26** (95% CI 1.23-1.29, p = 0.000) per +1 SD of campaign-window outage.
- Placebo (outage before the campaign): 1.24 (1.21-1.28). Outages before and during the campaign are correlated (both track rurality), so the placebo alone cannot separate the stories.
- Horse race (both in one model): campaign-window 1.21 (1.14-1.29), pre-campaign 1.04 (0.97-1.11). The cold-chain reading needs the campaign-window term above 1 and the pre-campaign term near 1.

See estimates.csv for every model and figures/ for plots. Read docs/pre_analysis_plan.md before interpreting anything.
