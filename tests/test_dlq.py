"""Tests para db.dlq (Dead Letter Queue)."""

from __future__ import annotations


def test_record_and_list(tmp_db):
    from db import dlq

    dlq.record_failure(
        "run-1", "bulk_202601", ValueError("bad payload"), scope="parse", payload_ref="f1.xml"
    )
    items = dlq.list_unresolved()
    assert len(items) == 1
    assert items[0]["error_type"] == "ValueError"
    assert items[0]["fuente"] == "bulk_202601"


def test_mark_resolved_removes_from_unresolved(tmp_db):
    from db import dlq

    dlq.record_failure("run-1", "bulk_202601", RuntimeError("x"))
    failure_id = dlq.list_unresolved()[0]["id"]
    dlq.mark_resolved(failure_id)
    assert dlq.list_unresolved() == []


def test_increment_retry(tmp_db):
    from db import dlq

    dlq.record_failure("run-1", "bulk_202601", RuntimeError("x"))
    failure_id = dlq.list_unresolved()[0]["id"]
    dlq.increment_retry(failure_id)
    dlq.increment_retry(failure_id)
    items = dlq.list_unresolved()
    assert items[0]["retry_count"] == 2


def test_record_failure_truncates_long_message(tmp_db):
    from db import dlq

    long_msg = "x" * 3000
    dlq.record_failure(None, "src", RuntimeError(long_msg))
    items = dlq.list_unresolved()
    assert len(items[0]["error_message"]) == 2000
