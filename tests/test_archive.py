import json
import os

from griddy.archive import GENESIS, append_events, verify_chain


def test_chain_appends_and_verifies(tmp_path):
    path = str(tmp_path / "events.jsonl")
    n = append_events(path, [{"ts": "t1", "event": "appeared", "key": "a", "case": {"x": 1}}])
    assert n == 1
    n = append_events(path, [{"ts": "t2", "event": "cleared", "key": "a", "case": {"x": 1}}])
    assert n == 1

    ok, msg = verify_chain(path)
    assert ok, msg
    assert "2 records" in msg

    lines = [json.loads(l) for l in open(path, encoding="utf-8")]
    assert lines[0]["seq"] == 1 and lines[0]["prev"] == GENESIS
    assert lines[1]["seq"] == 2 and lines[1]["prev"] != GENESIS


def test_tamper_is_detected(tmp_path):
    path = str(tmp_path / "events.jsonl")
    append_events(path, [{"ts": "t1", "event": "appeared", "key": "a", "case": {"x": 1}}])
    append_events(path, [{"ts": "t2", "event": "updated", "key": "a", "case": {"x": 2}}])

    # flip a value in line 1 without recomputing hashes
    lines = open(path, encoding="utf-8").read().splitlines()
    lines[0] = lines[0].replace('"x":1', '"x":9')
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

    ok, msg = verify_chain(path)
    assert not ok
    assert "mismatch" in msg


def test_empty_append_is_noop(tmp_path):
    path = str(tmp_path / "events.jsonl")
    assert append_events(path, []) == 0
    assert not os.path.exists(path)
