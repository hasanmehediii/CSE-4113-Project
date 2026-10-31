from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import Database, require_csrf, require_roles
from app.core.rate_limit import enforce
from app.models.civic import (
    Assignment,
    Complaint,
    PointEntry,
    WorkerApplication,
    WorkerLocation,
    now,
)
from app.schemas.civic import (
    AvailabilityInput,
    ResolutionVoteInput,
    WorkerApplicationInput,
    WorkerLocationInput,
)
from app.services import civic_service as service
from app.services.worker_service import submit_application

router = APIRouter(tags=["Community"], dependencies=[Depends(require_csrf)])
Member = Annotated[object, Depends(require_roles("citizen", "worker", "admin"))]
Citizen = Annotated[object, Depends(require_roles("citizen"))]
Worker = Annotated[object, Depends(require_roles("worker"))]


@router.get("/me/points")
def points(
    user: Member, db: Database,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    entries = db.scalars(
        select(PointEntry)
        .where(PointEntry.user_id == user.id)
        .order_by(PointEntry.created_at.desc(), PointEntry.id)
        .offset(offset).limit(limit)
    ).all()
    return {
        "balance": service.balance(db, user.id),
        "total": db.scalar(select(func.count()).select_from(PointEntry).where(PointEntry.user_id == user.id)),
        "entries": [
            {
                "id": e.id,
                "delta": e.delta,
                "reason": e.reason,
                "created_at": e.created_at,
                "complaint_id": e.complaint_id,
            }
            for e in entries
        ],
    }


@router.get("/me/complaints")
def my_complaints(
    user: Member, db: Database,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_total: bool = False,
):
    items = [service.public_complaint(db, row) for row in service.list_complaints(
        db, mine=user.id, limit=limit, offset=offset
    )]
    if not include_total:
        return items  # Preserve the existing array response for older clients.
    return {"items": items, "total": db.scalar(select(func.count()).select_from(Complaint).where(
        Complaint.author_id == user.id
    ))}


@router.get("/me/complaints/{complaint_id}/participation")
def participation(complaint_id: str, user: Member, db: Database):
    report = service.get_complaint(db, complaint_id)
    return {"is_reporter": db.scalar(select(Complaint.id).where(
        service.incident_members(report.incident_id or report.id), Complaint.author_id == user.id
    ).limit(1)) is not None}


@router.get("/workers/application")
def application(user: Member, db: Database):
    row = db.get(WorkerApplication, user.id)
    return (
        None
        if not row
        else {
            "status": row.status,
            "review_note": row.review_note,
            "submitted_at": row.submitted_at,
        }
    )


@router.post("/workers/application", status_code=202)
def apply(data: WorkerApplicationInput, user: Citizen, request: Request, db: Database):
    enforce(request, "worker-application", user.id, 3, 86400)
    # Lock user to serialize reapplications; worker role is granted only by admin review.
    db.refresh(user, with_for_update=True)
    existing = db.get(WorkerApplication, user.id)
    if existing and existing.status != "rejected":
        raise HTTPException(409, "Your application is already pending or approved")
    try:
        submit_application(db, user.id, data, existing)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This identity cannot be used for this application")
    return {"status": "pending"}


@router.put("/workers/location")
def location(data: WorkerLocationInput, user: Worker, db: Database):
    service.approved_worker(db, user.id)
    db.refresh(user, with_for_update=True)
    row = db.get(WorkerLocation, user.id) or WorkerLocation(user_id=user.id)
    row.latitude, row.longitude, row.available = data.latitude, data.longitude, data.available
    row.updated_at = now()
    db.add(row)
    return {"message": "Location updated", "expires_in_seconds": 900}


@router.get("/workers/assignments")
def assignments(
    user: Worker, db: Database,
    status: Literal["active", "completed", "cancelled"] | None = None,
    category: str | None = Query(default=None, max_length=40),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
):
    query = select(Assignment).where(Assignment.worker_id == user.id)
    if status:
        query = query.where(Assignment.status == status)
    if category:
        query = query.join(Complaint, Complaint.id == Assignment.complaint_id).where(
            Complaint.category_code == category
        )
    rows = db.scalars(
        query.order_by(Assignment.created_at.desc(), Assignment.id).offset(offset).limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "status": r.status,
            "source": r.source,
            "complaint": service.public_complaint(db, service.get_complaint(db, r.complaint_id)),
        }
        for r in rows
    ]


@router.patch("/workers/availability")
def availability(data: AvailabilityInput, user: Worker, db: Database):
    db.refresh(user, with_for_update=True)
    row = db.get(WorkerLocation, user.id)
    if data.available and (not row or row.updated_at < now() - 900):
        raise HTTPException(409, "Share a recent location before becoming available")
    if row:
        row.available = data.available
    return {"available": data.available}


@router.put("/resolutions/{resolution_id}/vote")
def resolution_vote(
    resolution_id: str, data: ResolutionVoteInput, user: Citizen, request: Request, db: Database
):
    enforce(request, "resolution-vote", user.id, 60, 3600)
    return service.vote_resolution(db, user, resolution_id, data)
