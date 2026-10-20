# Dhaka Main Road ML Dataset — English + বাংলা

> **SIMULATED / SYNTHETIC DATASET — NOT ACTUAL DHaka road observations.**
> **সব ডেটা সিমুলেশনে তৈরি; প্রকৃত সময়ের যানজট, বৃষ্টি বা রাস্তা বন্ধের রেকর্ড নয়।**

## Files

- `dhaka_major_roads_ml_dataset_bilingual.csv`: **20,790** supervised-learning rows, 47 bilingual + numeric columns, UTF-8 with BOM (Excel friendly).
- `dhaka_directed_road_segments_bilingual.csv`: **210** directional edges connecting 77 major junctions; join by `road_segment_id = segment_id`.
- `dhaka_major_road_nodes_bilingual.csv`: junction lookup, English and Bangla.
- `dhaka_train_bilingual.csv`, `dhaka_validation_bilingual.csv`, `dhaka_test_bilingual.csv`: time-separated splits.
- `dhaka_data_dictionary_bilingual.csv`: every column in English and বাংলা.
- `dhaka_dataset_stats.json`: counts and class rates.
- `generate_dhaka_dataset.py`: generator code (Python standard library; fixed seed).
- `dhaka_demo_route.py`: illustrative shortest-open-route program; not for live navigation.
- `background_sources.csv`: background reading, **not row-by-row evidence**.

## Scope / পরিধি

Only selected major arterial routes and big-junction connectors around Uttara, Mirpur, Banani/Gulshan, Badda/Rampura, central Dhaka, Dhanmondi and Motijheel.
Residential numbered block streets such as **Uttara Sector 6 Road 12** were intentionally excluded.

This is a **conceptual directed graph**. Roads, junctions and some corridor names are inspired by real places, but **precise topology, coordinates, road legality, direction, lane counts, lengths, and turning restrictions were NOT verified**. Each conceptual connection has two simulated directional edges. DO NOT use directly for real vehicle routing or flood safety decisions. Obtain road geometry and restrictions from OSM/authorized mapping sources before deployment.

## Targets / লেবেল

1. `target_traffic_blocked`: blocked/near standstill from traffic at target time (1 = yes).
2. `target_water_blocked`: modeled impassable by waterlogging at target time (1 = yes).
3. `target_any_blocked`: `max(traffic,water)`, an OR combination. If you train this from inputs, never feed the first two *true labels* as features.
4. `target_block_reason_en`/`_bn`: multiclass label (None / Traffic / Waterlogging / Both).
5. `target_travel_time_min_sim`: **future outcome** only on unblocked roads; blank on blocked roads.

Road risk, drainage, congestion, rainfall and speed are all invented but correlated by a seeded probabilistic scenario generator. **No real-world generalization or safety can be inferred from test scores on this data.**

## Prediction framing / আগাম পূর্বাভাস

- `issue_time_dhaka` = when you run the model; weather/history/recent-speed inputs are assumed available.
- `target_time_dhaka` = time you want to predict, (30, 60, 120) minutes later.
- `forecast_rain_target_1h_mm_sim` = assumed **weather forecast**, NOT observed future rainfall.
- `rainfall_last_*` = imagined accumulated rain before issue time; cumulative values are monotone.
- Train a classifier to predict each of the traffic and water labels using ONLY features available at issue time (plus known location/time metadata). Target time/horizon are valid inputs; future blockage/reason labels (`target_traffic_blocked`, `target_water_blocked`, `target_any_blocked`, `target_block_reason_en`, `target_block_reason_bn`) and `target_travel_time_min_sim` are leakage. `target_time_dhaka` is known at prediction time and is not leakage.

## Suggested ML columns

Numeric: `month`, `hour_24`, `is_weekend_fri_sat`, `is_peak_hour`, `forecast_horizon_min`, `estimated_length_km`, `assumed_lane_count`, `baseline_congestion_sim_0to1`, `flood_susceptibility_sim_0to1`, `drainage_capacity_sim_0to100`, `rainfall_last_1h_mm_sim`, `rainfall_last_3h_mm_sim`, `rainfall_last_6h_mm_sim`, `forecast_rain_target_1h_mm_sim`, `recent_speed_kmh_sim`, `traffic_demand_index_sim_0to100`, `nearby_event_sim_0or1`.

Categorical: `road_segment_id`, `zone`, `day_of_week_en`, `season_en`, `rain_condition_en`, `congestion_level_en`.

Metadata (not necessary to train): names in English and Bangla, `issue_time_dhaka`, `target_time_dhaka`, `data_origin`, `record_id`, `dataset_split`.

Do not train on both Bangla+English duplicates of identical fields; use one representation. **`target_any_blocked` can also be computed from two model predictions** instead of separately training all three models.

## Time-based evaluation

- Train 2024 = 7,560 rows
- Validation 2025 = 7,560 rows
- Test January–September 2026 = 5,670 rows
- Timeseries scenarios are shared by all roads at the same target time; never randomly split individual rows across train/test (would leak scenario conditions).
- Evaluate both labels with precision, recall, F1, PR-AUC and by major corridor/month; report class prevalence and failure rates.
- Models fitted on these rows learn the synthetic generator, **not Dhaka**.

## Routing / রুট নির্বাচন

Graph nodes: junction IDs. Edges: directed `segment_id` from the directed road CSV. For departure at time T, call the traffic + water classifiers for every candidate edge for that T/horizon; reject edges whose probability exceeds your threshold, or penalize edge expected travel time by predicted blockage risk, then use **Dijkstra / A-star**. If a segment is blocked, do not assign it a routable travel time. Demo route example reads **synthetic ground-truth target labels** purely for testing connectivity, not for model predictions. Actual deployment needs validated geospatial data, turn restrictions, up-to-date verified reports, and realistic travel-time prediction.

## Background reading (not input training data)
- BMD monsoon season background: https://bmd.gov.bd/file/2016/08/17/pdf/7037.pdf
- Daily Star 2025 structural waterlogging background: https://www.thedailystar.net/news/bangladesh/news/drainage-disaster-why-dhaka-drowns-every-monsoon-3907576
- bdnews24 2025 streets affected: https://bdnews24.com/bangladesh/336a8d2cadc9
- UNB 2024 DMP affected zones: https://unb.com.bd/category/Bangladesh/dmp-to-commuters-be-aware-of-rain-triggered-traffic-jams/139229
- BBA existing road networks report (government PDF): https://bba.gov.bd/sites/default/files/files/bba.portal.gov.bd/download/35dd6bf8_315f_48d2_98cc_d150d75b3adc/2024-10-24-09-17-b2375e1f087b89eee152532aa70487ec.pdf

## Validation summary (simulator only)
- Rows: **20,790** | directed edges: **210** | named junctions: **77** | synchronized times: **99**.
- Synthetic traffic-blocked: **4,368** (21.0%).
- Synthetic water-blocked: **770** (3.7%).
- Either cause: **4,809** (23.1%).

**Use in coursework / capstone:** Label methodology clearly as "simulation-generated". Replace synthetic forecasts and labels with verified historical weather, traffic speed and waterlogging observations for a credible predictive model. Consider police advisories, verified citizen reports, BMD rainfall, and OSM-based graph extraction (license/attribution required).
