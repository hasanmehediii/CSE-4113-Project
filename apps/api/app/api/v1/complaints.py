from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.dependencies import Database, require_csrf, require_roles
from app.core.rate_limit import enforce
from app.schemas.civic import ComplaintInput, EvidenceInput, ResolutionInput, VoteInput
from app.services import civic_service as service

router = APIRouter(prefix="/complaints", tags=["Complaints"], dependencies=[Depends(require_csrf)])
Contributor = Annotated[object, Depends(require_roles("citizen", "worker", "admin"))]
Citizen = Annotated[object, Depends(require_roles("citizen"))]
Worker = Annotated[object, Depends(require_roles("worker"))]


@router.get("")
def complaints(
    db: Database,
    status: str | None = None,
    category: str | None = None,
    q: str | None = Query(default=None, max_length=150),
    latitude: float | None = Query(default=None, ge=23.6, le=24),
    longitude: float | None = Query(default=None, ge=90.2, le=90.6),
    radius_km: float = Query(default=3, ge=0.1, le=20),
    limit: int = Query(default=30, ge=1, le=30),
    offset: int = Query(default=0, ge=0, le=10000),
    ranked: bool = False,
    all_reports: bool = False,
):
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "Supply both latitude and longitude")
    rows = service.list_complaints(
        db,
        status=status,
        category=category,
        q=q,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit,
        offset=offset,
        ranked=ranked,
        all_reports=all_reports,
    )
    return [service.public_complaint(db, row) for row in rows]


@router.post("", status_code=201)
def create(data: ComplaintInput, user: Contributor, request: Request, db: Database):
    enforce(request, "report-create", user.id, 10, 3600)
    return service.public_complaint(db, service.create_complaint(db, user, data), detail=True)


@router.get("/similar")
def similar(
    db: Database,
    latitude: float = Query(ge=23.6, le=24, allow_inf_nan=False),
    longitude: float = Query(ge=90.2, le=90.6, allow_inf_nan=False),
    category_code: str = Query(min_length=1, max_length=40),
    road_id: str | None = Query(default=None, max_length=36),
):
    return [service.public_complaint(db, row) for row in service.incident_candidates(
        db, latitude, longitude, category_code, road_id
    )]


@router.get("/{complaint_id}/reports")
def reports(
    complaint_id: str, db: Database,
    limit: int = Query(default=10, ge=1, le=30), offset: int = Query(default=0, ge=0),
):
    return service.incident_reports(db, complaint_id, limit, offset)


@router.get("/{complaint_id}")
def detail(complaint_id: str, db: Database):
    return service.public_complaint(db, service.get_complaint(db, complaint_id), detail=True)


@router.put("/{complaint_id}/vote")
def vote(complaint_id: str, data: VoteInput, user: Citizen, request: Request, db: Database):
    enforce(request, "community-vote", user.id, 60, 3600)
    return service.vote_complaint(db, user, complaint_id, data.value)


@router.post("/{complaint_id}/false-reports", status_code=201)
def false_report(complaint_id: str, data: EvidenceInput, user: Worker, db: Database):
    return service.false_report(db, user, complaint_id, data)


@router.post("/{complaint_id}/resolutions", status_code=201)
def resolve(complaint_id: str, data: ResolutionInput, user: Worker, db: Database):
    return service.resolve(db, user, complaint_id, data)
