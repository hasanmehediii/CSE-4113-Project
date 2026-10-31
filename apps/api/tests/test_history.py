"""History pages retain older records, totals, balances and account isolation."""
import pytest
import test_civic

from app.models.civic import Complaint, PointEntry


@pytest.fixture
def history_env(tmp_path, monkeypatch):
    yield from test_civic.civic_env.__wrapped__(tmp_path, monkeypatch)


def test_all_history_pages_keep_totals_and_balance_and_exclude_other_accounts(history_env):
    client, factory = history_env
    author = test_civic.account(factory, "history-author")
    other = test_civic.account(factory, "history-other")
    with factory() as db:
        reports = [Complaint(author_id=author, **test_civic.payload(), created_at=100 + i)
                   for i in range(35)]
        db.add_all(reports)
        db.flush()
        # Corroborating submissions remain individual personal-history records.
        reports[-1].incident_id = reports[0].id
        db.add(Complaint(author_id=other, **test_civic.payload(), created_at=999))
        db.add_all(PointEntry(user_id=author, delta=1, reason="complaint",
                             source_key=f"history:{i}", created_at=100 + i) for i in range(105))
        db.add(PointEntry(user_id=other, delta=900, reason="complaint", source_key="private"))
        db.commit()
        expected = [row.id for row in reversed(reports)]
    test_civic.sign_in(client, factory, author)
    assert len(client.get("/api/v1/me/complaints").json()) == 30  # Backward compatible.
    pages = [client.get(f"/api/v1/me/complaints?include_total=true&limit=30&offset={offset}").json()
             for offset in (0, 30, 60)]
    assert [row["id"] for page in pages for row in page["items"]] == expected
    assert all(page["total"] == 35 for page in pages)
    ledger = client.get("/api/v1/me/points").json()
    assert len(ledger["entries"]) == 100 and ledger["total"] == ledger["balance"] == 105
    pages = [client.get(f"/api/v1/me/points?limit=20&offset={offset}").json()
             for offset in range(0, 121, 20)]
    ids = [row["id"] for page in pages for row in page["entries"]]
    assert len(ids) == len(set(ids)) == 105
    assert all(page["balance"] == page["total"] == 105 for page in pages)
    assert pages[-1]["entries"] == []


@pytest.mark.parametrize("route", ["complaints", "points"])
def test_history_pagination_bounds_and_authentication(history_env, route):
    client, factory = history_env
    assert client.get(f"/api/v1/me/{route}").status_code == 401
    test_civic.sign_in(client, factory, test_civic.account(factory, "bounds"))
    for query in ("offset=-1", "limit=0", "limit=101"):
        assert client.get(f"/api/v1/me/{route}?{query}").status_code == 422


def test_participation_identifies_every_reporter_through_root_and_child_without_public_ids(history_env):
    client, factory = history_env
    first = test_civic.account(factory, "participation-first")
    second = test_civic.account(factory, "participation-second")
    independent = test_civic.account(factory, "participation-independent")
    test_civic.sign_in(client, factory, first)
    root = test_civic.create_report(client)
    test_civic.sign_in(client, factory, second)
    child = test_civic.create_report(client)
    for account, expected in ((first, True), (second, True), (independent, False)):
        test_civic.sign_in(client, factory, account)
        for report in (root, child):
            assert client.get(f"/api/v1/me/complaints/{report}/participation").json() == {"is_reporter": expected}
    assert client.get("/api/v1/me/complaints/missing/participation").status_code == 404
    client.cookies.clear()
    assert client.get(f"/api/v1/me/complaints/{root}/participation").status_code == 401
    public = client.get(f"/api/v1/complaints/{root}").json()
    assert "author_id" not in public and "is_reporter" not in public
