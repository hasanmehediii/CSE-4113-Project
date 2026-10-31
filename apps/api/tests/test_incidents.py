"""Corroboration is preserved; only the incident's work and status are shared."""
import pytest
import test_civic
from sqlalchemy import func, select

from app.models.civic import (
    Assignment,
    Complaint,
    ComplaintImage,
    ComplaintPrediction,
    ModerationCase,
    now,
)
from app.services.road_catalog import MAIN_ROADS, seed_main_roads


@pytest.fixture
def incident_env(tmp_path, monkeypatch):
    yield from test_civic.civic_env.__wrapped__(tmp_path, monkeypatch)


def submit(client, factory, user, **values):
    test_civic.sign_in(client, factory, user)
    result = client.post("/api/v1/complaints", headers=test_civic.headers(client),
                         json=test_civic.payload(**values))
    assert result.status_code == 201, result.text
    return result.json()


def test_many_reports_one_incident_with_all_evidence_and_one_point_per_person(incident_env):
    client, factory = incident_env
    first = test_civic.account(factory, "incident-first")
    second = test_civic.account(factory, "incident-second")
    root = submit(client, factory, first, images=["https://example.com/first.jpg"])
    extra = submit(client, factory, second, latitude=23.7512,
                   description="Another witness reports the same road blockage.",
                   images=["https://example.com/second.jpg"])
    again = submit(client, factory, second, description="A later photo from the same witness.")
    assert root["incident_id"] == root["id"]
    assert len({root["id"], extra["id"], again["id"]}) == 3
    assert extra["incident_id"] == again["incident_id"] == root["id"]
    assert again["incident_report_count"] == 3 and again["incident_reporter_count"] == 2
    assert [root["points_awarded"], extra["points_awarded"], again["points_awarded"]] == [1, 1, 0]
    assert client.get("/api/v1/me/points").json()["balance"] == 1
    assert len(client.get("/api/v1/me/complaints").json()) == 2
    assert len(client.get("/api/v1/complaints").json()) == 1
    assert len(client.get("/api/v1/complaints?all_reports=true").json()) == 3
    url = f"/api/v1/complaints/{extra['id']}/reports"
    reports = client.get(url + "?limit=2").json() + client.get(url + "?limit=2&offset=2").json()
    assert {row["id"] for row in reports} == {root["id"], extra["id"], again["id"]}
    saved = {row["id"]: row for row in reports}
    assert saved[root["id"]]["images"] == ["https://example.com/first.jpg"]
    assert saved[extra["id"]]["images"] == ["https://example.com/second.jpg"]
    assert saved[extra["id"]]["description"] == "Another witness reports the same road blockage."
    assert all("email" not in row and "phone" not in row for row in reports)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Complaint)) == 3
        assert db.scalar(select(func.count()).select_from(ComplaintImage)) == 2
        assert db.scalar(select(func.count()).select_from(ComplaintPrediction)) == 1
    assert client.put(f"/api/v1/complaints/{root['id']}/vote", headers=test_civic.headers(client),
                      json={"value": 1}).status_code == 403


def test_shared_assignment_completion_and_verification_from_any_report(incident_env):
    client, factory = incident_env
    first = test_civic.account(factory, "flow-first")
    second = test_civic.account(factory, "flow-second")
    root = submit(client, factory, first)
    extra = submit(client, factory, second)
    worker = test_civic.account(factory, "flow-worker", "worker")
    mayor = test_civic.account(factory, "flow-mayor", "admin")
    test_civic.sign_in(client, factory, mayor)
    response = client.post(f"/api/v1/admin/complaints/{extra['id']}/assign",
                           headers=test_civic.headers(client), json={"worker_id": worker})
    assert response.status_code == 201, response.text
    with factory() as db:
        assignments = db.scalars(select(Assignment)).all()
        assert len(assignments) == 1 and assignments[0].complaint_id == root["id"]
        assert db.get(Complaint, extra["id"]).status == "assigned"
    test_civic.sign_in(client, factory, worker)
    completed = client.post(f"/api/v1/complaints/{extra['id']}/resolutions",
                            headers=test_civic.headers(client), json={"comment": "The blockage has been cleared"})
    assert completed.status_code == 201
    for index in range(5):
        voter = test_civic.account(factory, f"incident-confirm-{index}")
        test_civic.sign_in(client, factory, voter)
        assert client.put(f"/api/v1/resolutions/{completed.json()['id']}/vote",
                          headers=test_civic.headers(client), json={"value": 1}).status_code == 200
    for report in (root, extra):
        detail = client.get(f"/api/v1/complaints/{report['id']}").json()
        assert detail["status"] == "resolved" and len(detail["resolutions"]) == 1
    later = submit(client, factory, second, description="A new blockage after the earlier incident was resolved.")
    assert later["incident_id"] == later["id"] != root["id"]
    assert later["points_awarded"] == 1


def test_separate_override_and_ambiguous_matches_require_a_choice(incident_env):
    client, factory = incident_env
    user = test_civic.account(factory, "separate-reporter")
    first = submit(client, factory, user)
    second = submit(client, factory, user, separate_incident=True)
    third_incident = submit(client, factory, user, separate_incident=True)
    assert first["incident_id"] != second["incident_id"]
    params = {"latitude": 23.751, "longitude": 90.375, "category_code": "road_flooding"}
    assert len(client.get("/api/v1/complaints/similar", params=params).json()) == 3
    response = client.post("/api/v1/complaints", headers=test_civic.headers(client),
                           json=test_civic.payload())
    assert response.status_code == 409
    third = submit(client, factory, user, incident_id=third_incident["id"])
    assert third["incident_id"] == third_incident["id"]
    assert third["points_awarded"] == 0
    assert client.post("/api/v1/complaints", headers=test_civic.headers(client),
                       json=test_civic.payload(incident_id=first["id"], separate_incident=True)).status_code == 422


@pytest.mark.parametrize("difference", ["far", "category", "resolved", "false", "expired"])
def test_unrelated_or_closed_incidents_never_match(incident_env, difference):
    client, factory = incident_env
    user = test_civic.account(factory, "unrelated-reporter")
    root = submit(client, factory, user)
    values = {}
    if difference == "far":
        values["latitude"] = 23.754
    elif difference == "category":
        values["category_code"] = "blocked_drain"
    else:
        with factory() as db:
            row = db.get(Complaint, root["id"])
            if difference == "expired":
                row.updated_at = now() - 86401
            else:
                row.status = difference
            db.commit()
    other = submit(client, factory, user, **values)
    assert other["incident_id"] == other["id"] != root["id"]
    assert client.post("/api/v1/complaints", headers=test_civic.headers(client),
                       json=test_civic.payload(**values, incident_id=root["id"])).status_code == 409


def test_matching_does_not_chain_down_a_long_road(incident_env):
    client, factory = incident_env
    user = test_civic.account(factory, "chain-reporter")
    first = submit(client, factory, user)
    nearby = submit(client, factory, user, latitude=23.7516)
    farther = submit(client, factory, user, latitude=23.7522)
    assert nearby["incident_id"] == first["id"]
    assert farther["incident_id"] == farther["id"]


@pytest.mark.parametrize("known_first", [True, False])
def test_known_road_boundaries_and_incident_analytics(incident_env, known_first):
    client, factory = incident_env
    with factory() as db:
        seed_main_roads(db)
        db.commit()
    road_ids = list(MAIN_ROADS)
    latitude, longitude = MAIN_ROADS[road_ids[0]]["center"]
    first = test_civic.account(factory, "road-first")
    second = test_civic.account(factory, "road-second")
    values = {"road_id": road_ids[0], "latitude": latitude, "longitude": longitude}
    root = submit(client, factory, first, **{**values, "road_id": road_ids[0] if known_first else None})
    extra = submit(client, factory, second, **values)
    assert extra["incident_id"] == root["id"]
    assert client.get(f"/api/v1/complaints/{root['id']}").json()["road_id"] == road_ids[0]
    road = next(row for row in client.get("/api/v1/map/roads").json() if row["id"] == road_ids[0])
    assert road["open_complaints"] == 1 and road["historical_reports_90d"] == 1
    assert sum(row["count"] for row in client.get("/api/v1/map/hotspots").json()) == 1
    mayor = test_civic.account(factory, "road-mayor", "admin")
    test_civic.sign_in(client, factory, mayor)
    stats = client.get("/api/v1/admin/analytics").json()
    assert stats["total_reports"] == 2 and stats["incident_count"] == 1
    assert stats["by_status"] == {"open": 1}
    other = submit(client, factory, second, **{**values, "road_id": road_ids[1]})
    assert other["incident_id"] == other["id"]


def test_road_observations_remain_independent_and_reporters_cannot_work_own_incident(incident_env):
    client, factory = incident_env
    citizen = test_civic.account(factory, "observation-citizen")
    worker = test_civic.account(factory, "observation-worker", "worker")
    root = submit(client, factory, citizen)
    extra = submit(client, factory, worker)
    mayor = test_civic.account(factory, "observation-mayor", "admin")
    test_civic.sign_in(client, factory, mayor)
    assert client.post(f"/api/v1/admin/complaints/{root['id']}/assign",
                       headers=test_civic.headers(client), json={"worker_id": worker}).status_code == 409
    first = submit(client, factory, citizen, kind="road_update", condition="good")
    second = submit(client, factory, citizen, kind="road_update", condition="good")
    assert first["incident_id"] is None and second["incident_id"] is None
    assert first["points_awarded"] == second["points_awarded"] == 1
    assert extra["incident_id"] == root["id"]


def test_incident_votes_false_threshold_and_moderation_are_shared(incident_env):
    client, factory = incident_env
    author = test_civic.account(factory, "moderated-author")
    witness = test_civic.account(factory, "moderated-witness")
    root = submit(client, factory, author)
    extra = submit(client, factory, witness)
    for index in range(5):
        voter = test_civic.account(factory, f"incident-dislike-{index}")
        test_civic.sign_in(client, factory, voter)
        # Voting through both URLs still records a single vote for the incident.
        for report in (root, extra):
            response = client.put(f"/api/v1/complaints/{report['id']}/vote",
                                  headers=test_civic.headers(client), json={"value": -1})
            assert response.status_code == 200 and response.json()["dislikes"] == index + 1
    for index in range(2):
        worker = test_civic.account(factory, f"incident-evidence-{index}", "worker")
        test_civic.sign_in(client, factory, worker)
        response = client.post(f"/api/v1/complaints/{extra['id']}/false-reports",
                               headers=test_civic.headers(client), json={
                                   "comment": "Independent evidence about this incident",
                                   "image_url": f"https://example.com/evidence-{index}.jpg",
                               })
        assert response.status_code == 201
    assert all(client.get(f"/api/v1/complaints/{row['id']}").json()["status"] == "false"
               for row in (root, extra))
    with factory() as db:
        case = db.scalar(select(ModerationCase))
        assert case.complaint_id == root["id"] and case.subject_user_id == author
        case_id = case.id
    mayor = test_civic.account(factory, "incident-moderator", "admin")
    test_civic.sign_in(client, factory, mayor)
    assert client.post(f"/api/v1/admin/moderation/{case_id}/review",
                       headers=test_civic.headers(client), json={
                           "status": "dismissed", "note": "The incident has been independently verified"
                       }).status_code == 200
    assert all(client.get(f"/api/v1/complaints/{row['id']}").json()["status"] == "open"
               for row in (root, extra))


def test_previous_votes_and_false_evidence_stop_counting_when_voter_becomes_reporter(incident_env):
    client, factory = incident_env
    author = test_civic.account(factory, "later-witness-author")
    root = submit(client, factory, author)
    voter = test_civic.account(factory, "later-witness-voter")
    test_civic.sign_in(client, factory, voter)
    url = f"/api/v1/complaints/{root['id']}"
    assert client.put(url + "/vote", headers=test_civic.headers(client),
                      json={"value": 1}).json()["likes"] == 1
    submit(client, factory, voter)
    assert client.get(url).json()["likes"] == 0
    for index in range(5):
        citizen = test_civic.account(factory, f"later-witness-dislike-{index}")
        test_civic.sign_in(client, factory, citizen)
        assert client.put(url + "/vote", headers=test_civic.headers(client),
                          json={"value": -1}).status_code == 200
    for index in range(3):
        worker = test_civic.account(factory, f"later-witness-worker-{index}", "worker")
        test_civic.sign_in(client, factory, worker)
        assert client.post(url + "/false-reports", headers=test_civic.headers(client), json={
            "comment": "Evidence from the independent inspection",
            "image_url": f"https://example.com/inspection-{index}.jpg",
        }).status_code == 201
        if index == 0:
            submit(client, factory, worker)
        assert client.get(url).json()["status"] == ("false" if index == 2 else "open")


def test_assigned_worker_who_later_reports_requires_reassignment(incident_env):
    client, factory = incident_env
    citizen = test_civic.account(factory, "assigned-witness-citizen")
    worker = test_civic.account(factory, "assigned-witness-worker", "worker")
    replacement = test_civic.account(factory, "assigned-witness-replacement", "worker")
    mayor = test_civic.account(factory, "assigned-witness-mayor", "admin")
    root = submit(client, factory, citizen)
    url = f"/api/v1/complaints/{root['id']}"
    assign_url = f"/api/v1/admin/complaints/{root['id']}/assign"
    test_civic.sign_in(client, factory, mayor)
    assert client.post(assign_url, headers=test_civic.headers(client),
                       json={"worker_id": worker}).status_code == 201
    submit(client, factory, worker)
    assert client.post(url + "/resolutions", headers=test_civic.headers(client),
                       json={"comment": "The blockage has been cleared"}).status_code == 409
    test_civic.sign_in(client, factory, mayor)
    assert client.post(assign_url, headers=test_civic.headers(client),
                       json={"worker_id": replacement, "reassign": True}).status_code == 201
    test_civic.sign_in(client, factory, replacement)
    assert client.post(url + "/resolutions", headers=test_civic.headers(client),
                       json={"comment": "The blockage has been independently cleared"}).status_code == 201
