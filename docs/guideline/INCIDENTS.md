# Many witnesses, one incident

Multiple citizens reporting one blockage are corroborating the same event. Their
reports are preserved; the worker queue should not create one independent job for
each witness. The original complaint is the incident's stable work ID and additional
complaint records reference it through `complaints.incident_id`.

## Matching and separation

The server matches new complaints against an active, same-category incident whose
latest report/workflow activity is within 24 hours, within 80 metres of its original
point. Every report is compared to the original anchor, preventing a chain of nearby
reports from grouping an entire long road. Two known different road IDs never match.
An unlinked incident can acquire its road association from a compatible later report.

One eligible incident is joined automatically. If more than one matches, submission
requires an explicit selection or `separate_incident: true`. Users can also force a
separate incident for a genuinely different nearby problem. Suggestions can be
refreshed without losing the draft. The server validates the match again at save time.
Resolved, false or stale incidents are excluded. Road observations are not grouped.

PostgreSQL serializes matching/insertion with a per-category transaction advisory
lock, including simultaneous first reports. This deliberately favors correctness
over high-volume throughput in the current MVP. Existing historical complaints are
not retroactively merged, especially where assignments or moderation already exist.

## Preserved records and shared actions

Each report keeps its ID, author, title, description, coordinates, timestamp and
images. Individual detail links and personal contributions still work. The incident
detail offers paginated access to all submissions and distinct reporter counts.

Assignment/reassignment, completion, verification, votes and moderation operate on
the shared incident even when requested through an additional report's URL. Status
changes propagate to every linked report. Reporters cannot vote on their own
incident, nor can a contributing worker be assigned to resolve it. A citizen can
vote only once per incident, not once per report URL.
If someone votes or tags false evidence before becoming a reporter, that record
stays stored but stops counting as independent incident evidence. An assigned
worker who later contributes a report must request reassignment before completion.

Each person receives at most one complaint contribution point per incident; repeat
submissions remain evidence but do not increase that person's points or distinct
reporter count. Road observations keep the existing one-point policy. Reporter
counts and these contribution limits use account IDs, not government-verified
identity. Phone OTP and automatic identity verification remain outside this feature.

False-incident moderation keeps the existing forfeiture policy for the original incident reporter;
it does not automatically forfeit every corroborating citizen's balance.

### Completion lifecycle and moderation

Only the current completion can receive verification votes. Starting a new work
assignment marks older completions `superseded_at`; their evidence, votes and
timestamps remain visible as read-only history. This marker does not depend on
timestamp ordering, so work submitted within the same second is handled safely.
A partial unique index permits at most one current completion per incident.

Dismissing false-incident moderation restores the current work state: pending
completion → `awaiting_confirmation`, confirmed completion → `resolved`, disputed
completion → `disputed`. If there is no current completion, the incident reopens;
unfinished assignments cancelled by the false ruling are not automatically revived.
An old completion or moderation review cannot overwrite a replacement work cycle.

Migration `20261031_06` preserves completion/vote records and marks superseded
legacy work. An already-stuck incident with an active replacement assignment is
restored to `assigned`. For older incidents with equally recent completion
timestamps, the migration does not guess a current completion from random IDs:
it retires the ambiguous completions and reopens the incident for a fresh assignment.
Existing points-ledger history is retained.

Queues, map/hotspot counts and work-status analytics count an incident once.
`total_reports` and per-incident report counts include every submission. Classification
is queued once for the incident, with its existing category-confidence fallback.

## API

- `GET /api/v1/complaints` lists incidents and independent road updates.
- `all_reports=true` returns every report; existing pagination still applies.
- `GET /api/v1/complaints/similar?latitude=...&longitude=...&category_code=...&road_id=...`
  returns up to 30 compatible incident suggestions; `road_id` is optional.
- `POST /api/v1/complaints` accepts optional `incident_id` to choose a compatible
  existing incident, or `separate_incident: true`; they cannot be combined.
- `GET /api/v1/complaints/{report_id}/reports?limit=10&offset=0` returns preserved
  submissions for that report's incident without exposing private account fields.
- Complaint responses include `incident_id`, `incident_report_count` and
  `incident_reporter_count`. Creation also returns `points_awarded` (0 or 1).

Apply migrations through `20261031_06` with `uv run alembic upgrade head` before using the
updated API. The root launchers do this automatically. Back up shared databases
before upgrading. The nullable link preserves existing data; the SQL snapshot is
stamped at the current migration head and its generator no longer rewrites history.

## Limits and next steps

This is an explicit matching rule, not semantic ML or proof that reports concern
the same physical blockage. A large incident can extend beyond the radius; two
different problems can be very close. Users should choose separate incidents when
appropriate. Administrative merge/split/relink tools and retrospective reconciliation
are future work. No evidence is deleted to make the queue appear deduplicated.
