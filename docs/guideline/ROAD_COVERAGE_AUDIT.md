# Road coverage and prediction explanation audit

Prepared: 20 November 2026 · Owner: Nafisha (task N3) · Base: `dev` at `b7748e6`

This audit checks how the road-risk dataset in `packages/new-data` is connected to
the 14 roads drawn on `/map`, and how the app explains what its predictions are.
It changes no mapping, model or training data.

## Reproduce

From `apps/ml-service`:

```powershell
uv run python -m app.audit_road_mapping          # readable report
uv run python -m app.audit_road_mapping --json   # machine-readable report
```

The command reads `packages/new-data/dhaka_directed_road_segments_bilingual.csv`,
`packages/data/dhaka-road-segment-mapping.json` and `packages/data/dhaka-main-roads.json`.
It exits with status 1 for structural errors: unknown segment IDs, a segment mapped
to more than one corridor, a segment mapped in one direction only, or a map corridor
without a mapping. Endpoint and length findings are printed as review notes.
`tests/test_road_mapping_audit.py` keeps the supplied mapping free of structural errors.

## Coverage counts

| Measure | Count |
| --- | ---: |
| Directed segments in the dataset (and in the trained model) | 210 |
| Segments mapped to a map corridor | 80 (38%) |
| Segments with no map overlay | 130 |
| Map corridors | 14 |
| Corridors with at least one mapped segment | 14 |
| Structural mapping errors | 0 |

Every mapped segment exists, is used by exactly one corridor and is mapped in both
simulated directions (`…A` and `…B`).

The 130 unmapped segments fall into two groups:

- **18 continuations outside the drawn corridors** — correctly unmapped. Airport Road
  `DHK001`–`DHK004` (Abdullahpur → Airport, north of the drawn Airport–Kakoli corridor),
  Begum Rokeya Sarani `DHK028`–`DHK030` (Mirpur 12 → Mirpur 10, before the drawn
  Mirpur 10 start) and Pragati Sarani `DHK018`–`DHK019` (Rampura → Malibagh, past the
  drawn Rampura end).
- **112 segments on 51 dataset roads with no map corridor** — for example Green Road
  (6), Panthapath (6) and Mirpur Main Road (4), plus the Farmgate Arterial Link removed
  from Manik Mia Avenue. The model is trained on them, but the map has no geometry to
  display them. Adding them needs new OpenStreetMap corridors
  (see [LIVE_MAP.md](LIVE_MAP.md#road-catalog-and-geometry)) and a retrained model.

## Per-corridor check

"Mapped km" adds the dataset's estimated lengths for one direction. "Drawn span" is
the straight-line distance between the corridor's two farthest OpenStreetMap points.
Roads curve, so a ratio of about 1.3–2.0 is normal; above 2.2 is flagged for review.

| Corridor | Segments | Mapped chain | Mapped km | Drawn span km | Result |
| --- | ---: | --- | ---: | ---: | --- |
| Airport Road · Airport–Kakoli | 8 | Airport → Kakoli | 8.9 | 6.32 | OK |
| Airport Road · Kakoli–Farmgate | 8 | Kakoli → Farmgate | 6.9 | 4.16 | OK |
| Begum Rokeya Sarani | 8 | Mirpur 10 → Bijoy Sarani | 7.0 | 4.93 | OK |
| Mirpur Road · Technical–Shyamoli | 4 | Technical Junction → Shyamoli | 3.0 | 1.73 | OK |
| Mirpur Road · Shyamoli–Science Lab | 6 | Shyamoli → Science Lab | 6.7 | 4.22 | OK |
| Mirpur Road · Science Lab–Azimpur | 6 | Science Lab → Azimpur | 2.7 | 1.36 | OK |
| Bijoy Sarani | 2 | Bijoy Sarani → Khejur Bagan | 1.9 | 0.58 | **Review** |
| Kazi Nazrul Islam Avenue | 6 | Farmgate → Shahbag | 4.7 | 2.42 | OK |
| Pragati Sarani | 10 | Kuril Bishwa Road → Rampura | 9.2 | 6.74 | OK |
| Manik Mia Avenue | 4 | Asad Gate → Khamarbari | 2.9 | 0.98 | **Review** (length only) |
| Satmasjid Road | 8 | Dhanmondi 27 → Mohammadpur Bus Stand | 6.2 | 2.54 | **Review** |
| Gulshan Avenue | 2 | Gulshan 2 → Gulshan 1 | 2.4 | 1.64 | OK |
| VIP Road · Kakrail–Motijheel | 6 | Kakrail → Motijheel | 4.0 | 1.67 | **Review** |
| Shahbagh–Matsya Bhaban Road | 2 | Shahbag → Matsya Bhaban | 1.4 | 0.94 | OK |

## Mapping findings

The supplied junctions have no coordinates, so these are findings from names and the
drawn geometry, not a surveyed validation. Each affects only that corridor's displayed
probability, which is the **highest** probability among its mapped segments.

1. **Manik Mia Avenue — corrected (issue #7).** The mapping used to continue one segment
   past the corridor's Khamar Bari end: `DHK057A/B` "Farmgate Arterial Link", Khamarbari →
   Farmgate (0.8 km). Both were removed from `dhaka-manik-mia` and the model was retrained
   (`road-risk-bilingual-v2-0a8c3fd5bb5a`; evaluation metrics unchanged). The chain now ends
   at Khamarbari. The remaining length note compares the dataset's estimated 2.9 km with a
   0.98 km straight-line span and needs the same geospatial check as the roads below.
2. **Bijoy Sarani — likely mismatch.** The drawn corridor is the short link from
   Begum Rokeya Sarani to the Airport Road junction (0.58 km). Its only mapped segment,
   `DHK058A/B` "Bijoy Sarani / Parliament Link", runs Bijoy Sarani → Khejur Bagan
   (1.9 km), which is a different stretch. The dataset has no segment for the drawn link.
   Suggested options: keep it with a documented approximation, or remove the corridor
   from predictions until a matching segment exists.
3. **Satmasjid Road — needs geospatial review.** The corridor runs Mohammadpur →
   Dhanmondi south. The mapped chain starts at Dhanmondi 27 and passes Kalabagan before
   Jigatola, Shankar and Mohammadpur Bus Stand, giving 6.2 km against a 2.54 km span.
   `DHK075`–`DHK076` (Jigatola → Shankar → Mohammadpur) match the drawn road best;
   `DHK073`–`DHK074` (via Kalabagan) should be checked against a map.
4. **VIP Road — needs geospatial review.** The endpoints match (Kakrail → Motijheel),
   but the dataset names the roads Naya Paltan Main Road, Fakirapool Main Road and
   Motijheel Main Connector, and the chain is 2.4× the drawn span.

The mapping was **not changed** in this task. A mapping change alters the trained
artifact's `road_segments` and `mapping_sha256`, so it requires retraining the
road-risk model and updating its published report
(`docs/model-reports/road-risk-new-data.report.json`). Agree the corrections as a team,
then change `packages/data/dhaka-road-segment-mapping.json`, retrain
([ROAD_DATASET_TRAINING.md](ROAD_DATASET_TRAINING.md)) and rerun this audit.

## Predictions versus observations

| What the user sees | Source | How it is shown |
| --- | --- | --- |
| Community reports and road updates (views 01 and 02) | Real users' reports and confirmed cleanups | Solid road colours; good updates expire after 24 hours |
| Predicted risk (view 03) | Random-forest model trained on the **synthetic** dataset | "SYNTHETIC MODEL · DEMO" badge, dashed lines, "not a verified forecast", "uncalibrated" labels |
| Scenario rainfall in view 03 | Typed by the user | Hint under the input (added in this task) |
| Dhaka weather widget (home page) | Open-Meteo live weather model | Note that predictions do not use it (added in this task) |

The prediction model receives only the target time, the forecast horizon and the
user's scenario rainfall, plus static road attributes. It does not receive live
weather, traffic speeds or community reports. Displayed probabilities measure what
the model learned from the simulator, not real-world Dhaka accuracy.

**The weather widget does not supply prediction rainfall.** It shows Open-Meteo's
current reading ("Rain · last 15 min") for information only. Prediction rainfall is
always the amount entered in "Scenario rainfall · mm in one hour".

### Wording added (review with Moin)

| Place | English | Bangla |
| --- | --- | --- |
| Under the scenario rainfall input | You choose this amount. It is not taken from the Dhaka weather widget or any live weather feed. | এই পরিমাণ আপনি নির্ধারণ করেন। এটি ঢাকার আবহাওয়া উইজেট বা কোনো সরাসরি আবহাওয়ার তথ্য থেকে নেওয়া হয় না। |
| Weather widget | For information only. Road-risk predictions on the map use the rainfall amount you enter, not this reading. | শুধু তথ্যের জন্য। মানচিত্রের রাস্তার ঝুঁকির পূর্বাভাসে এই তথ্য নয়, আপনার দেওয়া বৃষ্টির পরিমাণ ব্যবহার হয়। |

Both lines are covered by frontend tests in English and Bangla and were checked at
1366 × 900 and 390 × 844 without horizontal scrolling.

## Presentation summary

“The map covers 14 main-road corridors. They connect to 80 of the dataset's 210
synthetic road segments; the other 130 have no map geometry yet. Predictions come from
a model trained on simulated scenarios and the rainfall you type in; the weather widget
and community reports are not model inputs. Four corridor mappings are flagged for
geospatial review, and real-world accuracy has not been established.”
