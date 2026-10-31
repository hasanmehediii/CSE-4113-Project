"""Business rules; every mutation participates in the request's PostgreSQL transaction."""

import math

from fastapi import HTTPException
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.orm import Session, aliased

from app.models.civic import (
    Assignment,
    Category,
    Complaint,
    ComplaintImage,
    ComplaintPrediction,
    ComplaintVote,
    FalseReport,
    ModerationCase,
    OutboxEvent,
    PointEntry,
    Resolution,
    ResolutionVote,
    Road,
    WorkerApplication,
    WorkerLocation,
    now,
)
from app.models.user import User

OPEN = ("open", "assigned", "awaiting_confirmation", "disputed")
INCIDENT_RADIUS_KM = 0.08
INCIDENT_WINDOW_SECONDS = 86400


def event(db, event_type, aggregate_id, **payload):
    db.add(OutboxEvent(event_type=event_type, aggregate_id=aggregate_id, payload=payload))


def get_complaint(db, complaint_id, lock=False):
    if lock:
        # Always lock the incident before work/votes, even when opened through a
        # corroborating report. Group membership is immutable after submission.
        parent = db.scalar(select(Complaint.incident_id).where(Complaint.id == complaint_id))
        complaint_id = parent or complaint_id
    query = select(Complaint).where(Complaint.id == complaint_id)
    row = db.scalar(
        query.with_for_update().execution_options(populate_existing=True) if lock else query
    )
    if not row:
        raise HTTPException(404, "Complaint not found")
    return row


def incident_members(incident_id):
    return or_(Complaint.id == incident_id, Complaint.incident_id == incident_id)


def set_incident_status(db, row, status):
    row.status = status
    db.execute(update(Complaint).where(Complaint.incident_id == row.id).values(status=status))


def incident_candidates(db, latitude, longitude, category_code, road_id=None, *, lock=False, incident_id=None):
    query = select(Complaint).where(
        Complaint.kind == "complaint", Complaint.incident_id.is_(None),
        Complaint.status.in_(OPEN), Complaint.category_code == category_code,
        Complaint.updated_at >= now() - INCIDENT_WINDOW_SECONDS,
    )
    if road_id:
        query = query.where(or_(Complaint.road_id == road_id, Complaint.road_id.is_(None)))
    if incident_id:
        query = query.where(Complaint.id == incident_id)
    query = nearby(query, db, latitude, longitude, INCIDENT_RADIUS_KM)
    query = query.order_by(Complaint.created_at, Complaint.id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return db.scalars(query.limit(2 if lock and not incident_id else 30)).all()


def balance(db, user_id):
    return db.scalar(
        select(func.coalesce(func.sum(PointEntry.delta), 0)).where(PointEntry.user_id == user_id)
    )


def points(db, user_id, delta, reason, source_key, complaint_id=None, resolution_id=None):
    # Serializes account credits, deductions and reversals; the ledger is authoritative.
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    if db.scalar(select(PointEntry.id).where(PointEntry.source_key == source_key)):
        return
    db.add(
        PointEntry(
            user_id=user_id,
            delta=delta,
            reason=reason,
            source_key=source_key,
            complaint_id=complaint_id,
            resolution_id=resolution_id,
        )
    )
    db.flush()


def create_complaint(db: Session, user: User, data):
    if not db.get(Category, data.category_code):
        raise HTTPException(422, "Unknown category")
    if data.road_id and not db.get(Road, data.road_id):
        raise HTTPException(422, "Unknown road")
    parent = None
    if data.kind == "complaint":
        if db.bind.dialect.name == "postgresql":
            # Serialize matching and insertion, including the first two reports
            # of an incident. A per-category transaction lock also covers nearby
            # points on opposite sides of a geographic grid boundary.
            db.execute(select(func.pg_advisory_xact_lock(func.hashtext(
                "incident-group:" + data.category_code
            ))))
        if not data.separate_incident:
            candidates = incident_candidates(
                db, data.latitude, data.longitude, data.category_code, data.road_id,
                lock=True, incident_id=data.incident_id,
            )
            if data.incident_id:
                parent = next((row for row in candidates if row.id == data.incident_id), None)
                if not parent:
                    raise HTTPException(409, "That incident is no longer an eligible match. Refresh the nearby incidents.")
            elif len(candidates) > 1:
                raise HTTPException(409, "Several nearby incidents match. Choose one or mark this as a separate incident.")
            elif candidates:
                parent = candidates[0]
    row = Complaint(
        author_id=user.id,
        **data.model_dump(exclude={"images", "incident_id", "separate_incident"}),
        incident_id=parent.id if parent else None,
        status=parent.status if parent else "open",
    )
    db.add(row)
    if parent and not row.road_id:
        row.road_id = parent.road_id
    db.flush()
    if row.kind == "complaint" and not parent:
        db.add(ComplaintPrediction(complaint_id=row.id))
    if parent:
        parent.updated_at = now()
        # A precise unlinked report can be associated with a known road by a
        # later corroborating report; two known, different roads never match.
        if not parent.road_id and data.road_id:
            parent.road_id = data.road_id
    db.add_all(ComplaintImage(complaint_id=row.id, url=url) for url in data.images)
    canonical_id = parent.id if parent else row.id
    previous = db.scalar(select(Complaint.id).where(
        incident_members(canonical_id), Complaint.author_id == user.id, Complaint.id != row.id
    ).limit(1)) if row.kind == "complaint" else None
    row.points_awarded = 0 if previous else 1
    if not previous:
        source = f"incident:{canonical_id}:{user.id}" if row.kind == "complaint" else f"report:{row.id}"
        points(db, user.id, 1, row.kind, source, row.id)
    event(
        db,
        "complaint.created",
        row.id,
        kind=row.kind,
        incident_id=canonical_id if row.kind == "complaint" else None,
        road_id=row.road_id,
        category_code=row.category_code,
        location={"type": "Point", "coordinates": [row.longitude, row.latitude]},
    )
    return row


def vote_counts(db, model, target_field, target_id):
    query = (
        select(model.value, func.count())
        .join(User, User.id == model.user_id)
        .where(
            target_field == target_id,
            User.role == "citizen",
            User.is_active.is_(True),
            User.email_verified.is_(True),
        )
        .group_by(model.value)
    )
    if model is ComplaintVote:
        # A voter can later become a witness. Preserve their vote record, but it
        # must no longer count as an independent vote on their own incident.
        query = query.where(~select(Complaint.id).where(
            incident_members(target_id), Complaint.author_id == User.id
        ).exists())
    rows = db.execute(query).all()
    counts = dict(rows)
    return {"likes": counts.get(1, 0), "dislikes": counts.get(-1, 0)}


def check_false(db, row):
    if row.status == "false":
        return
    if db.scalar(select(ModerationCase.id).where(ModerationCase.source_key == f"false:{row.id}")):
        return  # An administrator's adjudication is final for this report.
    votes = vote_counts(db, ComplaintVote, ComplaintVote.complaint_id, row.id)
    workers = db.scalar(
        select(func.count())
        .select_from(FalseReport)
        .join(User, User.id == FalseReport.worker_id)
        .join(WorkerApplication, WorkerApplication.user_id == User.id)
        .where(
            FalseReport.complaint_id == row.id,
            User.is_active.is_(True),
            User.role == "worker",
            WorkerApplication.status == "approved",
            ~select(Complaint.id).where(
                incident_members(row.id), Complaint.author_id == User.id
            ).exists(),
        )
    )
    if votes["dislikes"] < 5 or workers < 2:
        return
    # Serialize against concurrent credits before reading the balance for forfeiture.
    db.scalar(select(User).where(User.id == row.author_id).with_for_update())
    points(
        db,
        row.author_id,
        -balance(db, row.author_id),
        "false_report_forfeiture",
        f"false:{row.id}",
        row.id,
    )
    set_incident_status(db, row, "false")
    for assignment in db.scalars(
        select(Assignment).where(Assignment.complaint_id == row.id, Assignment.status == "active")
    ):
        assignment.status = "cancelled"
    db.add(
        ModerationCase(
            subject_user_id=row.author_id,
            complaint_id=row.id,
            source_key=f"false:{row.id}",
            kind="false_complaint",
        )
    )
    event(db, "complaint.false", row.id, subject_user_id=row.author_id)


def vote_complaint(db, user, complaint_id, value):
    row = get_complaint(db, complaint_id, lock=True)
    if db.scalar(select(Complaint.id).where(
        incident_members(row.id), Complaint.author_id == user.id
    ).limit(1)):
        raise HTTPException(403, "You cannot vote on your own report")
    if row.status == "false":
        raise HTTPException(409, "This report has been marked false")
    vote = db.get(ComplaintVote, (row.id, user.id))
    if vote:
        vote.value = value
    else:
        db.add(ComplaintVote(complaint_id=row.id, user_id=user.id, value=value))
    db.flush()
    check_false(db, row)
    return vote_counts(db, ComplaintVote, ComplaintVote.complaint_id, row.id)


def false_report(db, worker, complaint_id, data):
    row = get_complaint(db, complaint_id, lock=True)
    if db.scalar(select(Complaint.id).where(
        incident_members(row.id), Complaint.author_id == worker.id
    ).limit(1)):
        raise HTTPException(403, "You cannot tag your own report")
    if row.status == "false":
        raise HTTPException(409, "This report has already been marked false")
    if db.get(FalseReport, (row.id, worker.id)):
        raise HTTPException(409, "You have already submitted evidence")
    db.add(FalseReport(complaint_id=row.id, worker_id=worker.id, **data.model_dump()))
    db.flush()
    check_false(db, row)
    event(db, "complaint.false_evidence", row.id, worker_id=worker.id)
    return {"status": row.status}


def distance_km(lat1, lon1, lat2, lon2):
    lat1, lat2, dlon = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(a)))


def nearby(query, db, latitude, longitude, radius_km):
    if db.bind.dialect.name == "postgresql":
        origin = func.ll_to_earth(latitude, longitude)
        location = func.ll_to_earth(Complaint.latitude, Complaint.longitude)
        distance = func.earth_distance(origin, location)
        return query.where(
            func.earth_box(origin, radius_km * 1000).op("@>")(location),
            distance <= radius_km * 1000,
        ).order_by(distance)
    # SQLite test fallback; production uses the indexed spherical query above.
    ids = [
        r.id
        for r in db.scalars(select(Complaint))
        if distance_km(latitude, longitude, r.latitude, r.longitude) <= radius_km
    ]
    return query.where(Complaint.id.in_(ids))


def list_complaints(
    db,
    *,
    status=None,
    category=None,
    q=None,
    mine=None,
    latitude=None,
    longitude=None,
    radius_km=3,
    limit=30,
    offset=0,
    ranked=False,
    all_reports=False,
):
    query = select(Complaint)
    if not all_reports and mine is None:
        query = query.where(Complaint.incident_id.is_(None))
    if status == "unsolved":
        query = query.where(Complaint.status.in_(OPEN), Complaint.kind == "complaint")
    elif status:
        query = query.where(Complaint.status == status)
    if category:
        query = query.where(Complaint.category_code == category)
    if q:
        # Literal search: escape user wildcard characters.
        value = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            (Complaint.title + " " + Complaint.description + " " + Complaint.address).ilike(
                f"%{value}%", escape="\\"
            )
        )
    if mine:
        query = query.where(Complaint.author_id == mine)
    if latitude is not None and longitude is not None:
        query = nearby(query, db, latitude, longitude, radius_km)
    if ranked:
        predicted = aliased(Category)
        priority = case(
            (ComplaintPrediction.confidence >= 0.6, predicted.base_priority),
            else_=Category.base_priority,
        )
        query = (
            query.join(Category, Category.code == Complaint.category_code)
            .outerjoin(ComplaintPrediction, ComplaintPrediction.complaint_id == Complaint.id)
            .outerjoin(predicted, predicted.code == ComplaintPrediction.predicted_category)
            .order_by(priority.desc(), Complaint.created_at)
        )
    else:
        if mine is None and not all_reports:
            query = query.order_by(Complaint.updated_at.desc())
        query = query.order_by(Complaint.created_at.desc(), Complaint.id)
    return db.scalars(query.limit(limit).offset(offset)).all()


def public_complaint(db, row, detail=False):
    root = db.get(Complaint, row.incident_id) if row.incident_id else row
    author = db.get(User, row.author_id)
    result = {
        key: getattr(row, key)
        for key in (
            "id",
            "road_id",
            "category_code",
            "kind",
            "title",
            "description",
            "address",
            "latitude",
            "longitude",
            "condition",
            "status",
            "created_at",
            "updated_at",
        )
    }
    result["author_name"] = author.name if author else "Resident"
    result["status"] = root.status
    result["incident_id"] = root.id if row.kind == "complaint" else None
    counts = db.execute(select(
        func.count(Complaint.id), func.count(Complaint.author_id.distinct())
    ).where(incident_members(root.id))).one()
    result["incident_report_count"], result["incident_reporter_count"] = counts
    if hasattr(row, "points_awarded"):
        result["points_awarded"] = row.points_awarded
    result["images"] = list(
        db.scalars(select(ComplaintImage.url).where(ComplaintImage.complaint_id == row.id))
    )
    result.update(vote_counts(db, ComplaintVote, ComplaintVote.complaint_id, root.id))
    result["priority"] = db.get(Category, row.category_code).base_priority
    result["priority_source"] = "category_rules"
    prediction = db.get(ComplaintPrediction, root.id)
    result["classification"] = None
    if prediction and prediction.status == "ready":
        result["classification"] = {
            "category": prediction.predicted_category,
            "confidence": prediction.confidence,
            "model_version": prediction.model_version,
        }
        if prediction.confidence >= 0.6:
            result["priority"] = db.get(Category, prediction.predicted_category).base_priority
            result["priority_source"] = "ml_category_rules"
    if detail:
        assignment = db.scalar(
            select(Assignment).where(
                Assignment.complaint_id == root.id, Assignment.status == "active"
            )
        )
        result["active_assignment"] = {"worker_id": assignment.worker_id} if assignment else None
        resolutions = db.scalars(
            select(Resolution)
            .where(Resolution.complaint_id == root.id)
            .order_by(Resolution.created_at.desc())
        ).all()
        result["resolutions"] = [resolution_output(db, r) for r in resolutions]
    return result


def incident_reports(db, report_id, limit=10, offset=0):
    report = get_complaint(db, report_id)
    root_id = report.incident_id or report.id
    rows = db.execute(
        select(Complaint, User.name).join(User, User.id == Complaint.author_id)
        .where(incident_members(root_id))
        .order_by(Complaint.created_at, Complaint.id).offset(offset).limit(limit)
    ).all()
    return [{
        "id": row.id, "title": row.title, "description": row.description,
        "address": row.address, "latitude": row.latitude, "longitude": row.longitude,
        "author_name": name, "created_at": row.created_at,
        "images": list(db.scalars(select(ComplaintImage.url).where(ComplaintImage.complaint_id == row.id))),
    } for row, name in rows]


def resolution_output(db, row):
    worker = db.get(User, row.worker_id)
    return {
        "id": row.id,
        "worker_name": worker.name,
        "worker_id": row.worker_id,
        "comment": row.comment,
        "image_url": row.image_url,
        "status": row.status,
        "superseded": row.superseded_at is not None,
        "created_at": row.created_at,
        **vote_counts(db, ResolutionVote, ResolutionVote.resolution_id, row.id),
    }


def approved_worker(db, worker_id):
    worker = db.scalar(
        select(User).where(User.id == worker_id).with_for_update()
        .execution_options(populate_existing=True)
    )
    application = db.get(WorkerApplication, worker_id)
    if (
        not worker
        or not worker.is_active
        or worker.role != "worker"
        or not application
        or application.status != "approved"
    ):
        raise HTTPException(422, "Select an active approved worker")
    return worker


def assign(db, actor, complaint_id, worker_id=None, *, reassign=False):
    row = get_complaint(db, complaint_id, lock=True)
    allowed = {"assigned"} if reassign else {"open", "disputed"}
    if row.kind != "complaint" or row.status not in allowed:
        if reassign:
            raise HTTPException(409, "Only assigned complaints can be reassigned")
        raise HTTPException(409, "Only open or disputed complaints can be assigned")
    previous = db.scalar(
        select(Assignment).where(
            Assignment.complaint_id == row.id, Assignment.status == "active"
        ).with_for_update()
    )
    if reassign and not previous:
        raise HTTPException(409, "This complaint no longer has an active assignment")
    source = "admin" if worker_id else "system"
    reporters = set(db.scalars(select(Complaint.author_id).where(incident_members(row.id))))
    if not worker_id:
        locations = db.scalars(
            select(WorkerLocation)
            .join(User, User.id == WorkerLocation.user_id)
            .join(WorkerApplication, WorkerApplication.user_id == User.id)
            .where(
                WorkerLocation.available.is_(True),
                WorkerLocation.updated_at >= now() - 900,
                User.is_active.is_(True),
                User.role == "worker",
                WorkerApplication.status == "approved",
            )
        ).all()
        excluded = reporters | {previous.worker_id if previous else None}
        locations = [loc for loc in locations if loc.user_id not in excluded]
        if not locations:
            raise HTTPException(
                409, "No available workers with a location updated in the last 15 minutes"
            )
        loads = dict(
            db.execute(
                select(Assignment.worker_id, func.count())
                .where(Assignment.status == "active")
                .group_by(Assignment.worker_id)
            ).all()
        )
        worker_id = min(
            locations,
            key=lambda loc: (
                loads.get(loc.user_id, 0),
                distance_km(row.latitude, row.longitude, loc.latitude, loc.longitude),
                loc.user_id,
            ),
        ).user_id
    approved_worker(db, worker_id)
    if worker_id in reporters:
        raise HTTPException(409, "A worker cannot resolve their own report")
    if previous:
        if previous.worker_id == worker_id:
            raise HTTPException(409, "This worker is already assigned to the complaint")
        previous.status = "cancelled"
        # Release the partial unique index before inserting the replacement.
        db.flush()
    assignment = Assignment(
        complaint_id=row.id, worker_id=worker_id, assigned_by=actor.id, source=source
    )
    supersede_resolutions(db, row.id)
    db.add(assignment)
    set_incident_status(db, row, "assigned")
    db.flush()
    event(
        db, "complaint.reassigned" if previous else "complaint.assigned", row.id,
        worker_id=worker_id, source=source,
        previous_worker_id=previous.worker_id if previous else None,
    )
    return {"id": assignment.id, "worker_id": worker_id, "source": source}


def resolve(db, worker, complaint_id, data):
    row = get_complaint(db, complaint_id, lock=True)
    assignment = db.scalar(
        select(Assignment)
        .where(Assignment.complaint_id == row.id, Assignment.status == "active")
        .with_for_update()
    )
    if not assignment or assignment.worker_id != worker.id:
        raise HTTPException(403, "Only the assigned worker can submit completion")
    if db.scalar(select(Complaint.id).where(
        incident_members(row.id), Complaint.author_id == worker.id
    ).limit(1)):
        raise HTTPException(409, "A worker cannot resolve their own incident; request reassignment")
    if row.status != "assigned":
        raise HTTPException(409, "Complaint is not ready for completion")
    supersede_resolutions(db, row.id)
    resolution = Resolution(
        assignment_id=assignment.id, complaint_id=row.id, worker_id=worker.id, **data.model_dump()
    )
    db.add(resolution)
    assignment.status, assignment.completed_at = "completed", now()
    set_incident_status(db, row, "awaiting_confirmation")
    db.flush()
    event(db, "resolution.submitted", resolution.id, complaint_id=row.id, worker_id=worker.id)
    return resolution_output(db, resolution)


def supersede_resolutions(db, complaint_id):
    # Explicit ownership survives same-second submissions and later moderation.
    # Keep the original completion, evidence, votes and award history intact.
    db.execute(update(Resolution).where(
        Resolution.complaint_id == complaint_id, Resolution.superseded_at.is_(None)
    ).values(superseded_at=now()))


def current_resolution(db, complaint_id):
    return db.scalar(select(Resolution).join(Assignment, Assignment.id == Resolution.assignment_id).where(
        Resolution.complaint_id == complaint_id, Resolution.superseded_at.is_(None),
        Assignment.status == "completed",
    ))


def has_active_assignment(db, complaint_id):
    return db.scalar(select(Assignment.id).where(
        Assignment.complaint_id == complaint_id, Assignment.status == "active"
    ).limit(1)) is not None


def vote_resolution(db, user, resolution_id, data):
    candidate = db.get(Resolution, resolution_id)
    if not candidate:
        raise HTTPException(404, "Resolution not found")
    row = get_complaint(db, candidate.complaint_id, lock=True)
    resolution = db.scalar(
        select(Resolution)
        .where(Resolution.id == resolution_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if resolution.worker_id == user.id:
        raise HTTPException(403, "You cannot verify your own work")
    current = current_resolution(db, row.id)
    expected_status = {"pending": "awaiting_confirmation", "confirmed": "resolved"}.get(resolution.status)
    if (
        not current or current.id != resolution.id or row.status != expected_status
        or has_active_assignment(db, row.id)
    ):
        raise HTTPException(409, "This completion is no longer current or is under review")
    if data.value == -1 and db.scalar(
        select(ModerationCase.id).where(
            ModerationCase.source_key == f"dispute:{resolution.id}", ModerationCase.status != "open"
        )
    ):
        raise HTTPException(409, "This completion has already been reviewed by an administrator")
    previous = db.get(ResolutionVote, (resolution.id, user.id))
    if previous:
        previous.value, previous.image_url, previous.comment = (
            data.value,
            data.image_url,
            data.comment,
        )
    else:
        db.add(ResolutionVote(resolution_id=resolution.id, user_id=user.id, **data.model_dump()))
    db.flush()
    counts = vote_counts(db, ResolutionVote, ResolutionVote.resolution_id, resolution.id)
    if data.value == -1:
        # A single evidenced dispute is escalated; it does not automatically block a worker.
        if resolution.status == "confirmed":
            db.scalar(select(User).where(User.id == resolution.worker_id).with_for_update())
            points(
                db,
                resolution.worker_id,
                -min(5, balance(db, resolution.worker_id)),
                "resolution_disputed",
                f"dispute:{resolution.id}",
                row.id,
                resolution.id,
            )
        resolution.status = "disputed"
        set_incident_status(db, row, "disputed")
        db.add(
            ModerationCase(
                subject_user_id=resolution.worker_id,
                complaint_id=row.id,
                resolution_id=resolution.id,
                source_key=f"dispute:{resolution.id}",
                kind="worker_dispute",
            )
        )
        event(db, "resolution.disputed", resolution.id, complaint_id=row.id)
    elif counts["likes"] >= 5 and resolution.status == "pending":
        resolution.status, resolution.confirmed_at = "confirmed", now()
        set_incident_status(db, row, "resolved")
        points(
            db,
            resolution.worker_id,
            5,
            "resolution_confirmed",
            f"resolve:{resolution.id}",
            row.id,
            resolution.id,
        )
        event(db, "resolution.confirmed", resolution.id, complaint_id=row.id)
    return resolution_output(db, resolution)


def review_case(db, case_id, admin, data):
    candidate = db.get(ModerationCase, case_id)
    if not candidate:
        raise HTTPException(404, "Case not found")
    # Use the same complaint-first lock order as voting and assignment.
    complaint = get_complaint(db, candidate.complaint_id, lock=True)
    row = db.scalar(
        select(ModerationCase)
        .where(ModerationCase.id == case_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row.status != "open":
        raise HTTPException(409, "Case has already been reviewed")
    if data.status == "dismissed":
        source = (
            f"false:{complaint.id}"
            if row.kind == "false_complaint"
            else f"dispute:{row.resolution_id}"
        )
        if row.kind == "false_complaint":
            if complaint.status != "false":
                raise HTTPException(409, "This complaint has moved on; record the review as actioned")
            resolution = current_resolution(db, complaint.id)
            if has_active_assignment(db, complaint.id):
                restored = "assigned"
            elif resolution:
                restored = {
                    "pending": "awaiting_confirmation", "confirmed": "resolved", "disputed": "disputed"
                }[resolution.status]
            else:
                # A false ruling cancelled unfinished work; do not reactivate it.
                restored = "open"
            set_incident_status(db, complaint, restored)
        else:
            resolution = current_resolution(db, complaint.id)
            if (
                complaint.status != "disputed" or not resolution or resolution.id != row.resolution_id
                or has_active_assignment(db, complaint.id)
            ):
                raise HTTPException(
                    409, "This complaint has moved on; record the review as actioned"
                )
            resolution.status = "confirmed" if resolution.confirmed_at else "pending"
            set_incident_status(db, complaint, "resolved" if resolution.confirmed_at else "awaiting_confirmation")
        deduction = db.scalar(select(PointEntry).where(PointEntry.source_key == source))
        if deduction and deduction.delta < 0:
            points(
                db,
                row.subject_user_id,
                -deduction.delta,
                "moderation_restoration",
                f"restore:{row.id}",
                complaint.id,
                row.resolution_id,
            )
    row.status, row.note, row.reviewed_by, row.reviewed_at = data.status, data.note, admin.id, now()
    event(db, "moderation.reviewed", row.id, admin_id=admin.id, status=row.status, note=data.note)
    return {"status": row.status}
