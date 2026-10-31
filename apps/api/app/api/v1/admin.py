from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, func, or_, select, update
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import Database, require_csrf, require_roles
from app.models.civic import (
    Area,
    Complaint,
    FalseReport,
    ModerationCase,
    PointEntry,
    ResolutionVote,
    Road,
    WorkerApplication,
    now,
)
from app.models.user import AuthSession, User
from app.schemas.civic import (
    AreaInput,
    AssignInput,
    BlockInput,
    CaseReviewInput,
    ReviewInput,
    RoadInput,
)
from app.services import civic_service as service

router = APIRouter(prefix="/admin", tags=["Administration"], dependencies=[Depends(require_csrf)])
Admin = Annotated[object, Depends(require_roles("admin"))]


@router.get("/users")
def users(
    admin: Admin,
    db: Database,
    q: str = Query(default="", max_length=100),
    role: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
):
    query = select(User)
    if q:
        query = query.where(
            or_(
                User.name.icontains(q, autoescape=True),
                User.email.icontains(q, autoescape=True),
                User.phone.icontains(q, autoescape=True),
            )
        )
    if role:
        query = query.where(User.role == role)
    rows = db.scalars(
        query.order_by(User.created_at.desc(), User.id).offset(offset).limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "email": r.email,
            "phone": r.phone,
            "role": r.role,
            "is_active": r.is_active,
            "email_verified": r.email_verified,
            "points": service.balance(db, r.id),
        }
        for r in rows
    ]


@router.patch("/users/{user_id}/block")
def block(user_id: str, data: BlockInput, admin: Admin, db: Database):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "admin":
        raise HTTPException(403, "Administrator accounts cannot be blocked here")
    user.is_active = not data.blocked
    if data.blocked:
        db.execute(update(AuthSession).where(AuthSession.user_id == user.id).values(revoked=True))
    service.event(
        db,
        "user.block_changed",
        user.id,
        admin_id=admin.id,
        blocked=data.blocked,
        reason=data.reason,
    )
    return {"is_active": user.is_active}


@router.get("/worker-applications")
def applications(
    admin: Admin, db: Database, status: str = "pending", offset: int = Query(default=0, ge=0)
):
    rows = db.execute(
        select(WorkerApplication, User)
        .join(User, User.id == WorkerApplication.user_id)
        .where(WorkerApplication.status == status)
        .order_by(WorkerApplication.submitted_at)
        .offset(offset)
        .limit(30)
    ).all()
    return [
        {
            "user_id": a.user_id,
            "name": u.name,
            "email": u.email,
            "status": a.status,
            "has_nid_number": bool(a.nid_digest),
            "nid_image_url": a.nid_image_url,
            "submitted_at": a.submitted_at,
        }
        for a, u in rows
    ]


@router.post("/worker-applications/{user_id}/review")
def review(user_id: str, data: ReviewInput, admin: Admin, db: Database):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    application = db.get(WorkerApplication, user_id)
    if not application or not user:
        raise HTTPException(404, "Application not found")
    if application.status != "pending":
        raise HTTPException(409, "Application has already been reviewed")
    if not user.is_active or user.role != "citizen":
        raise HTTPException(409, "Applicant is not an active citizen")
    application.status = "approved" if data.approve else "rejected"
    application.reviewed_at, application.reviewed_by, application.review_note = (
        now(),
        admin.id,
        data.note,
    )
    if data.approve:
        user.role = "worker"
    service.event(db, "worker.reviewed", user_id, admin_id=admin.id, status=application.status)
    return {"status": application.status}


@router.post("/complaints/{complaint_id}/assign", status_code=201)
def assign(complaint_id: str, data: AssignInput, admin: Admin, db: Database):
    return service.assign(db, admin, complaint_id, data.worker_id, reassign=data.reassign)


@router.get("/moderation")
def moderation(
    admin: Admin, db: Database, status: str = "open", offset: int = Query(default=0, ge=0)
):
    rows = db.scalars(
        select(ModerationCase)
        .where(ModerationCase.status == status)
        .order_by(ModerationCase.created_at.desc())
        .offset(offset)
        .limit(30)
    ).all()
    results = []
    for row in rows:
        subject = db.get(User, row.subject_user_id)
        evidence = (
            [
                {"worker_id": r.worker_id, "image_url": r.image_url, "comment": r.comment}
                for r in db.scalars(
                    select(FalseReport).where(FalseReport.complaint_id == row.complaint_id)
                )
            ]
            if row.kind == "false_complaint"
            else [
                {"user_id": r.user_id, "image_url": r.image_url, "comment": r.comment}
                for r in db.scalars(
                    select(ResolutionVote).where(
                        ResolutionVote.resolution_id == row.resolution_id,
                        ResolutionVote.value == -1,
                    )
                )
            ]
        )
        results.append(
            {
                "id": row.id,
                "subject_user_id": row.subject_user_id,
                "subject_name": subject.name,
                "complaint_id": row.complaint_id,
                "kind": row.kind,
                "status": row.status,
                "evidence": evidence,
            }
        )
    return results


@router.post("/moderation/{case_id}/review")
def case_review(case_id: str, data: CaseReviewInput, admin: Admin, db: Database):
    return service.review_case(db, case_id, admin, data)


@router.get("/analytics")
def analytics(admin: Admin, db: Database):
    statuses = dict(
        db.execute(select(Complaint.status, func.count()).group_by(Complaint.status)).all()
    )
    categories = dict(
        db.execute(
            select(Complaint.category_code, func.count()).group_by(Complaint.category_code)
        ).all()
    )
    areas = db.execute(
        select(
            Area.name,
            func.count(Complaint.id),
            func.sum(func.cast(Complaint.status == "resolved", Integer)),
        )
        .join(Road, Road.area_id == Area.id)
        .join(Complaint, Complaint.road_id == Road.id)
        .group_by(Area.name)
        .order_by(func.count(Complaint.id).desc())
        .limit(20)
    ).all()
    leaders = db.execute(
        select(User.id, User.name, func.sum(PointEntry.delta).label("points"))
        .join(PointEntry, PointEntry.user_id == User.id)
        .where(User.is_active.is_(True))
        .group_by(User.id, User.name)
        .order_by(func.sum(PointEntry.delta).desc())
        .limit(10)
    ).all()
    return {
        "by_status": statuses,
        "by_category": categories,
        "by_area": [{"area": a, "total": n, "resolved": r} for a, n, r in areas],
        "leaders": [{"id": i, "name": n, "points": p} for i, n, p in leaders],
        "unmapped_reports": db.scalar(
            select(func.count()).select_from(Complaint).where(Complaint.road_id.is_(None))
        ),
        "users": db.scalar(select(func.count()).select_from(User)),
        "workers": db.scalar(select(func.count()).select_from(User).where(User.role == "worker")),
    }


def save_catalog(db, model, data):
    row = model(**data.model_dump())
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An entry with this name already exists")
    return {"id": row.id}


@router.post("/areas", status_code=201)
def add_area(data: AreaInput, admin: Admin, db: Database):
    return save_catalog(db, Area, data)


@router.post("/roads", status_code=201)
def add_road(data: RoadInput, admin: Admin, db: Database):
    if not db.get(Area, data.area_id):
        raise HTTPException(422, "Unknown area")
    return save_catalog(db, Road, data)
