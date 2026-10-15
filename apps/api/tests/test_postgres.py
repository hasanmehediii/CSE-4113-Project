"""Opt-in real database tests. Creates and drops ONLY randomly named test databases.

RUN_POSTGRES_TESTS=1 uv run pytest tests/test_postgres.py -q
Requires local Docker Postgres and MongoDB. Uses no production/user tables.
"""

import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from pymongo import MongoClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.models.civic import (
    Complaint,
    ComplaintVote,
    FalseReport,
    ModerationCase,
    OutboxEvent,
    PointEntry,
    WorkerApplication,
)
from app.models.user import User
from app.schemas.civic import ComplaintInput, EvidenceInput
from app.services import civic_service as service
from app.workers.project_events import project_batch

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_POSTGRES_TESTS") != "1", reason="Opt-in Docker integration tests"
)
ROOT = Path(__file__).resolve().parents[3]
API_ROOT = ROOT / "apps/api"


@pytest.fixture(scope="module")
def databases():
    base = make_url(
        os.environ.get(
            "TEST_POSTGRES_ADMIN_URL",
            "postgresql+psycopg://dubsibhai:local-dev-only@127.0.0.1:5432/postgres",
        )
    )
    names = ["dubsibhai_test_" + uuid.uuid4().hex[:12] for _ in range(2)]
    admin_url = base.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as admin:
        try:
            for name in names:
                admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            url = base.set(database=names[0]).render_as_string(hide_password=False)
            env = {**os.environ, "DATABASE_URL": url}
            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                env=env,
                cwd=API_ROOT,
                check=True,
                timeout=60,
                capture_output=True,
            )
            snapshot_url = base.set(drivername="postgresql", database=names[1]).render_as_string(
                hide_password=False
            )
            with psycopg.connect(snapshot_url, autocommit=True, connect_timeout=5) as snapshot:
                snapshot.execute((ROOT / "db/schema.sql").read_text(encoding="utf-8"))
            engine = create_engine(url, connect_args={"connect_timeout": 5})
            yield sessionmaker(engine, expire_on_commit=False), snapshot_url
            engine.dispose()
        finally:
            for name in names:
                assert name.startswith("dubsibhai_test_")
                admin.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
                )


def test_migration_snapshot_indexes_and_spatial_search(databases):
    factory, snapshot_url = databases
    with factory() as db, psycopg.connect(snapshot_url) as snapshot:
        migrated = (
            db.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
                )
            )
            .scalars()
            .all()
        )
        fresh = [
            r[0]
            for r in snapshot.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            )
        ]
        assert migrated == fresh
        assert (
            snapshot.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            == "20261015_03"
        )
        indexes = {
            r[0]
            for r in snapshot.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public'")
        }
        assert {
            "ix_complaints_geo",
            "ix_complaints_search",
            "uq_assignment_active",
            "ix_prediction_retry",
        } <= indexes
        author = User(
            name="Geo integration", email="geo-integration@example.com", email_verified=True
        )
        db.add(author)
        db.flush()
        row = service.create_complaint(
            db,
            author,
            ComplaintInput(
                title="Nearby drainage issue",
                description="There is water overflowing on the road.",
                address="Dhanmondi Road 12",
                latitude=23.751,
                longitude=90.375,
                category_code="road_flooding",
            ),
        )
        db.commit()
        assert row.id in [
            r.id for r in service.list_complaints(db, latitude=23.75, longitude=90.375, radius_km=1)
        ]
        assert not service.list_complaints(db, latitude=23.9, longitude=90.55, radius_km=1)


def test_concurrent_false_threshold_deducts_once(databases):
    factory, _ = databases
    with factory() as db:
        author = User(
            name="Concurrent author", email="concurrent-author@example.com", email_verified=True
        )
        voters = [
            User(name=f"Citizen {i}", email=f"concurrent-{i}@example.com", email_verified=True)
            for i in range(5)
        ]
        workers = [
            User(
                name=f"Worker {i}",
                email=f"concurrent-worker-{i}@example.com",
                email_verified=True,
                role="worker",
            )
            for i in range(2)
        ]
        db.add_all([author, *voters, *workers])
        db.flush()
        for worker in workers:
            db.add(
                WorkerApplication(user_id=worker.id, status="approved", nid_digest=uuid.uuid4().hex)
            )
        row = service.create_complaint(
            db,
            author,
            ComplaintInput(
                title="Concurrent threshold report",
                description="A report for concurrent threshold testing.",
                address="Dhanmondi Road 12",
                latitude=23.751,
                longitude=90.375,
                category_code="road_flooding",
            ),
        )
        db.add_all(ComplaintVote(complaint_id=row.id, user_id=v.id, value=-1) for v in voters[:4])
        db.add(
            FalseReport(
                complaint_id=row.id,
                worker_id=workers[0].id,
                image_url="https://example.com/first.jpg",
                comment="First independent evidence",
            )
        )
        db.commit()
        complaint_id, voter_id, worker_id, author_id = (
            row.id,
            voters[4].id,
            workers[1].id,
            author.id,
        )

    def last_vote():
        with factory() as db:
            service.vote_complaint(db, db.get(User, voter_id), complaint_id, -1)
            db.commit()

    def last_evidence():
        with factory() as db:
            service.false_report(
                db,
                db.get(User, worker_id),
                complaint_id,
                EvidenceInput(
                    image_url="https://example.com/second.jpg",
                    comment="Second independent evidence",
                ),
            )
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(last_vote), pool.submit(last_evidence)]
        for future in futures:
            future.result(timeout=15)
    with factory() as db:
        assert db.get(Complaint, complaint_id).status == "false"
        assert service.balance(db, author_id) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(PointEntry)
                .where(PointEntry.source_key == f"false:{complaint_id}")
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(ModerationCase)
                .where(ModerationCase.complaint_id == complaint_id)
            )
            == 1
        )


def test_real_mongo_projection_and_replay(databases):
    factory, _ = databases
    client = MongoClient(
        os.environ.get("TEST_MONGODB_URL", "mongodb://127.0.0.1:27017"),
        serverSelectionTimeoutMS=5000,
    )
    name = "dubsibhai_test_" + uuid.uuid4().hex[:12]
    mongo = client[name]
    try:
        with factory() as db:
            project_batch(db, mongo)
            count = mongo.civic_events.count_documents({})
            assert count > 0
            row = db.scalar(select(OutboxEvent))
            event_id = row.id
            row.delivered_at = None
            db.commit()
            assert project_batch(db, mongo) == 1
            assert mongo.civic_events.count_documents({}) == count
            assert mongo.civic_events.count_documents({"_id": event_id}) == 1
    finally:
        assert name.startswith("dubsibhai_test_")
        client.drop_database(name)
        client.close()
