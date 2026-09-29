import asyncio
from datetime import timedelta
from uuid import uuid4


async def enqueue_test_job(*, available_delta=0, max_attempts=3):
    from marcus.core.db import SessionFactory
    from marcus.core.security import now
    from marcus.database.models import Job

    job_id = str(uuid4())
    async with SessionFactory.begin() as session:
        session.add(
            Job(
                id=job_id,
                kind="cleanup",
                target_id=str(uuid4()),
                dedupe_key=f"test:{job_id}",
                payload={"type": "media"},
                available_at=now() + timedelta(seconds=available_delta),
                max_attempts=max_attempts,
            )
        )
    return job_id


async def test_mysql_skip_locked_two_workers_claim_different_jobs(db):
    from marcus.jobs.worker import claim_job

    expected = {await enqueue_test_job(), await enqueue_test_job()}
    first, second = await asyncio.gather(claim_job("worker-a"), claim_job("worker-b"))
    assert first and second
    assert {first["id"], second["id"]} == expected
    assert first["lease_owner"] == "worker-a" and second["lease_owner"] == "worker-b"
    assert await claim_job("worker-c") is None
    assert await db.scalar("SELECT COUNT(*) FROM jobs WHERE status='running' AND attempts=1") == 2


async def test_expired_lease_is_reclaimed_and_old_worker_cannot_write(db):
    from marcus.jobs.worker import claim_job, finish_job, renew_job

    job_id = await enqueue_test_job()
    first = await claim_job("worker-a")
    assert first is not None
    assert first["id"] == job_id
    await db.execute(
        "UPDATE jobs SET lease_until=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND WHERE id=:id", {"id": job_id}
    )
    second = await claim_job("worker-b")
    assert second is not None
    assert second["id"] == job_id and second["attempts"] == 2
    assert not await renew_job(job_id, "worker-a")
    assert not await finish_job(job_id, "worker-a")
    assert await renew_job(job_id, "worker-b")
    assert await finish_job(job_id, "worker-b")
    assert not await finish_job(job_id, "worker-b")
    row = (await db.rows("SELECT status,lease_owner,lease_until FROM jobs WHERE id=:id", {"id": job_id}))[0]
    assert row["status"] == "succeeded" and row["lease_owner"] is None and row["lease_until"] is None


async def test_failed_job_backoff_and_attempt_limit(db):
    from marcus.jobs.worker import claim_job, finish_job

    job_id = await enqueue_test_job(max_attempts=2)
    first = await claim_job("worker-a")
    assert first is not None
    assert first["id"] == job_id
    assert await finish_job(job_id, "worker-a", "temporary_failure")
    assert await claim_job("worker-b") is None
    await db.execute(
        "UPDATE jobs SET available_at=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND WHERE id=:id", {"id": job_id}
    )
    second = await claim_job("worker-b")
    assert second is not None
    assert second["attempts"] == 2
    assert await finish_job(job_id, "worker-b", "temporary_failure")
    assert await db.scalar("SELECT status FROM jobs WHERE id=:id", {"id": job_id}) == "failed"
    assert await claim_job("worker-c") is None


async def test_future_job_is_not_claimed_and_expired_max_attempt_is_terminal(db):
    from marcus.jobs.worker import claim_job

    future = await enqueue_test_job(available_delta=3600)
    exhausted = await enqueue_test_job(max_attempts=1)
    claimed = await claim_job("worker-a")
    assert claimed is not None
    assert claimed["id"] == exhausted
    await db.execute(
        "UPDATE jobs SET lease_until=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND WHERE id=:id", {"id": exhausted}
    )
    assert await claim_job("worker-b") is None
    assert await db.scalar("SELECT status FROM jobs WHERE id=:id", {"id": exhausted}) == "failed"
    assert await db.scalar("SELECT status FROM jobs WHERE id=:id", {"id": future}) == "queued"
