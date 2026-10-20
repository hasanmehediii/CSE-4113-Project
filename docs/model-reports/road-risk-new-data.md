# Road-risk training result: supplied bilingual dataset

Model: `road-risk-bilingual-v2-5a9298fc817c`. Trained: 2026-10-20T21:14:09.453841+06:00.

Used the CSVs in `packages/new-data`, preserving the supplied chronological partitions:
7,560 training rows (2024), 7,560 validation rows (2025), and 5,670 test rows (January–September 2026).
Model/threshold selection uses validation data. The final model fits 15,120 training-plus-validation
rows; the 2026 test rows are excluded from fitting. These are development holdout results,
not an independently blinded or real-world validation.

The data contains 210 directed segments and only 99 shared time scenarios. The existing map's
14 corridors are explicitly mapped to 82 of these segments; inference displays the maximum
segment probability for each hazard. Other segments are training coverage, not new map geometry.

## Held-out segment results

| Target | Decision threshold | Precision | Recall | F1 | Average precision | Brier score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| waterlogging | 0.05 | 0.0670 | 0.6027 | 0.1205 | 0.1560 | 0.0240 |
| traffic_jam | 0.20 | 0.2825 | 0.7335 | 0.4079 | 0.2955 | 0.1560 |

Decision thresholds maximize validation F1. They are separate from the map's 35%/65% probability
color bands. Detailed results at the default 0.5 threshold are also saved; both targets have
zero recall there. The low waterlogging precision means many false alerts, and traffic precision
is also limited. Do not interpret high recall as high overall reliability.

The constant-prevalence baseline average precision is 0.0258 for waterlogging and 0.2058 for
traffic. The learned model ranks synthetic risks better than this baseline, but classification
quality is weak, especially for waterlogging. No real-world performance is established.

## Feature availability

The model uses 13 features available to the current map: target time, forecast horizon, user
scenario rainfall and static assumed road attributes. It excludes future outcome columns and
also excludes recent speed, past rainfall, traffic demand and events because the app cannot
supply them. Their absence limits predictive information. No live telemetry is fabricated.

Selected forest settings: 128 trees, max depth 10,
minimum leaf size 20, seed 42.
The probabilities are uncalibrated. The source files explicitly identify all data as simulated;
road topology and geographic accuracy are unverified.

## Reproducibility

Observation CSV SHA-256: `f01f9bb31abff68c34abcc198002548e29d18de11d21a9df1ad3a4574ace39c5`.

Mapping SHA-256: `17ec83173c54a90fc2c839bec1962eb0897efe34e5f01e43285ddbd3b0cf35f2`.

Training code SHA-256: `ac46901c860a6afdc51375b44f67cfde35720481a912384545949ef7deab9db6`.

See [the full JSON report](road-risk-new-data.report.json) for candidate comparisons,
monthly/corridor breakdowns and source hashes. [Training and deployment instructions](../guideline/ROAD_DATASET_TRAINING.md).
