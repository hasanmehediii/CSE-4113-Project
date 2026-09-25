# drainage_complaints_bn.csv — Synthetic Bengali Drainage Complaint Dataset

## What this is
360 synthetic Bengali complaint sentences, template-generated (not real user
reports), balanced across 6 categories (60 each) matching DrainWatch's
classifier design in `SYSTEM_DESIGN.md`:

| category | meaning |
|---|---|
| `blocked_drain` | Drain clogged with garbage/debris |
| `open_manhole` | Missing or open manhole cover — safety hazard |
| `road_flooding` | Acute flooding after rain, road impassable |
| `waterlogging_recurring` | Same spot floods repeatedly, chronic issue |
| `sewage_overflow` | Sewage line overflow, contamination risk |
| `other` | Construction issues, general drainage complaints, unclear category |

Each row: `id`, `text_bn` (the complaint text), `category` (label).

## How it was generated
`generate_dataset.py` fills hand-written Bengali sentence templates per
category with randomized slots: 25 Dhaka-area names, optional time phrases
("গতকাল রাত থেকে" / since last night), and optional severity phrases. This
gives lexical variety without needing real complaint text, and every
sentence is grammatically valid Bengali.

**Re-run/expand it:**
```bash
python3 generate_dataset.py
```
Edit `SAMPLES_PER_CATEGORY`, `AREAS`, or add more templates to
`CATEGORY_TEMPLATES` to grow the dataset — more template variety per
category matters more than raw row count for how well this generalizes.

## Honest limitations (say this in your report)
- **This is not real user data.** Template generation means the model will
  learn your templates' phrasing patterns, not the full diversity of how
  real residents actually write complaints (typos, code-mixing with
  English, dialectal variation, terser/ruder phrasing, etc.).
- Treat this as a **bootstrapping/prototyping dataset** — good enough to
  build and demo the full pipeline (train → evaluate → serve →
  integrate with the monolith), but before any real deployment claim,
  the model should be retrained on genuine complaint text.
- For your lab report: state plainly that no public Bengali dataset for
  civic drainage complaints exists (verified via search — Bengali NLP
  resources are concentrated in news classification, sentiment, and hate
  speech), and that you built this synthetic set to unblock model
  development, same pattern as any lab exercise where placeholder data is
  used to validate a pipeline before real data arrives.

## Suggested next steps
1. Train/validate a TF-IDF + Logistic Regression baseline on this set
   first (fast, matches the "beginner friendly, simple" pattern from your
   ML lab) before attempting to fine-tune a transformer like banglabert.
2. In parallel, start collecting a small real sample (20-30 real examples
   per category from public Facebook posts/news about Dhaka waterlogging,
   with permission/attribution) to validate whether the synthetic-trained
   model transfers, and to eventually replace/augment this file.
3. Keep the CSV schema (`id`, `text_bn`, `category`) stable — this is what
   `apps/ml-service/app/models/classifier.py` should expect to load.
