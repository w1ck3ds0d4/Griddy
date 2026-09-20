import json

from griddy.stats import (
    COMPENSATION_THRESHOLD_HOURS,
    build_report,
    group_outages,
    locality_stats,
    summary,
    weekly_counts,
)


def _write(path, events):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def _case(outage_id, localities):
    return {"OutageId": outage_id, "Localities": localities}


def test_group_outages_pairs_appeared_and_cleared_by_outage_id():
    events = [
        {"ts": "2026-08-01T10:00:00+00:00", "key": "a", "event": "appeared", "case": _case(1, "Gudja, Luqa")},
        {"ts": "2026-08-01T17:00:00+00:00", "key": "a", "event": "cleared", "case": _case(1, "Gudja, Luqa")},
    ]
    outages = group_outages(events)
    assert len(outages) == 1
    o = outages[0]
    assert o["duration_hours"] == 7.0
    assert o["compensation_eligible"] is True
    assert o["localities"] == ["Gudja", "Luqa"]
    assert o["ongoing"] is False


def test_group_outages_groups_split_cases_sharing_outage_id():
    # Two raw case records (different keys) for the same real-world outage.
    events = [
        {"ts": "2026-08-01T10:00:00+00:00", "key": "a", "event": "appeared", "case": _case(9, "Zabbar")},
        {"ts": "2026-08-01T10:10:00+00:00", "key": "b", "event": "appeared", "case": _case(9, "Fgura")},
        {"ts": "2026-08-01T11:00:00+00:00", "key": "b", "event": "cleared", "case": _case(9, "Fgura")},
    ]
    outages = group_outages(events)
    assert len(outages) == 1
    assert outages[0]["localities"] == ["Fgura", "Zabbar"]


def test_short_outage_is_not_compensation_eligible():
    events = [
        {"ts": "2026-08-01T10:00:00+00:00", "key": "a", "event": "appeared", "case": _case(1, "Mosta")},
        {"ts": "2026-08-01T12:00:00+00:00", "key": "a", "event": "cleared", "case": _case(1, "Mosta")},
    ]
    outages = group_outages(events)
    assert outages[0]["duration_hours"] == 2.0
    assert outages[0]["compensation_eligible"] is False


def test_uncleared_outage_is_ongoing_with_no_duration():
    events = [
        {"ts": "2026-08-01T10:00:00+00:00", "key": "a", "event": "appeared", "case": _case(1, "Mosta")},
    ]
    outages = group_outages(events)
    assert outages[0]["ongoing"] is True
    assert outages[0]["duration_hours"] is None
    assert outages[0]["compensation_eligible"] is False


def test_locality_stats_aggregates_across_shared_localities():
    outages = group_outages(
        [
            {"ts": "2026-08-01T00:00:00+00:00", "key": "a", "event": "appeared", "case": _case(1, "Mosta")},
            {"ts": "2026-08-01T07:00:00+00:00", "key": "a", "event": "cleared", "case": _case(1, "Mosta")},
            {"ts": "2026-08-02T00:00:00+00:00", "key": "b", "event": "appeared", "case": _case(2, "Mosta")},
            {"ts": "2026-08-02T01:00:00+00:00", "key": "b", "event": "cleared", "case": _case(2, "Mosta")},
        ]
    )
    rows = locality_stats(outages)
    assert len(rows) == 1
    assert rows[0]["locality"] == "Mosta"
    assert rows[0]["outages"] == 2
    assert rows[0]["downtime_hours"] == 8.0
    assert rows[0]["eligible"] == 1


def test_weekly_counts_buckets_by_iso_week_start():
    outages = group_outages(
        [
            {"ts": "2026-08-03T09:00:00+00:00", "key": "a", "event": "appeared", "case": _case(1, "Mosta")},
            {"ts": "2026-08-04T09:00:00+00:00", "key": "b", "event": "appeared", "case": _case(2, "Mosta")},
        ]
    )
    weeks = weekly_counts(outages)
    assert weeks == [{"week": "2026-08-03", "outages": 2}]


def test_summary_counts_and_thresholds():
    outages = group_outages(
        [
            {"ts": "2026-08-01T00:00:00+00:00", "key": "a", "event": "appeared", "case": _case(1, "Mosta")},
            {"ts": "2026-08-01T07:00:00+00:00", "key": "a", "event": "cleared", "case": _case(1, "Mosta")},
            {"ts": "2026-08-02T00:00:00+00:00", "key": "b", "event": "appeared", "case": _case(2, "Mosta")},
        ]
    )
    s = summary(outages)
    assert s["total_outages"] == 2
    assert s["ongoing_outages"] == 1
    assert s["cleared_outages"] == 1
    assert s["compensation_eligible_outages"] == 1
    assert s["compensation_threshold_hours"] == COMPENSATION_THRESHOLD_HOURS
    assert s["household_compensation_eur"] == [60, 110]


def test_build_report_reads_missing_file_as_empty(tmp_path):
    report = build_report(str(tmp_path / "does-not-exist.jsonl"))
    assert report["summary"]["total_outages"] == 0
    assert report["by_locality"] == []
    assert report["weekly"] == []


def test_build_report_reads_live_jsonl(tmp_path):
    path = str(tmp_path / "live.jsonl")
    _write(
        path,
        [
            {"ts": "2026-08-01T00:00:00+00:00", "key": "a", "event": "appeared", "case": _case(1, "Mosta")},
            {"ts": "2026-08-01T09:00:00+00:00", "key": "a", "event": "cleared", "case": _case(1, "Mosta")},
        ],
    )
    report = build_report(path)
    assert report["summary"]["compensation_eligible_outages"] == 1
    assert report["outages"][0]["group_id"] == "1"
