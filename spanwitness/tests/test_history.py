"""History decisions, capture limits and durable evidence, not field accuracy."""
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from spanwitness.history import compare_pole_history, history_plan, observation_time
from spanwitness.history_examples import render_history_scene
from spanwitness.vision import analyze, decode_image, encode_image


def pair(case, seed=417):
    images, reports = [], []
    for view in ["baseline", "current"]:
        frame, geometry = render_history_scene(case, view, seed)
        frame = decode_image(encode_image(frame))
        report, _, _ = analyze(frame, None, geometry["pole"], geometry["vertical_reference"])
        images.append(frame)
        reports.append(report)
    return images, reports


@pytest.mark.parametrize("seed", [417, 821, 1907])
@pytest.mark.parametrize("case,status", [("alignment-change", "change_detected"),
    ("camera-roll", "no_material_change"), ("perspective", "not_comparable"), ("blurred", "not_comparable")])
def test_history_distinguishes_change_from_bad_evidence(case, status, seed):
    images, reports = pair(case, seed)
    result = compare_pole_history(*images, *reports, repeatable_capture=True)
    assert result["status"] == status
    if case == "alignment-change":
        assert abs(result["change_deg"] - 5) < .4
    elif case == "camera-roll":
        assert abs(result["change_deg"]) < .4
        assert abs(result["estimated_camera_rotation_deg"]) > 7
    else:
        assert result["change_deg"] is None


def test_unconfirmed_capture_and_reused_file_do_not_produce_change_measurements():
    images, reports = pair("alignment-change")
    result = compare_pole_history(*images, *reports)
    assert result["reason_code"] == "capture_not_confirmed" and result["change_deg"] is None
    result = compare_pole_history(*images, *reports, repeatable_capture=True, same_file=True)
    assert result["reason_code"] == "reused_image" and result["change_deg"] is None


def test_different_marked_reference_is_not_a_deterioration_measurement():
    images, reports = pair("alignment-change")
    geometry = render_history_scene("alignment-change", "current")[1]
    reports[1], _, _ = analyze(images[1], None, geometry["pole"], [[.93, .13], [.93, .86]])
    result = compare_pole_history(*images, *reports, repeatable_capture=True)
    assert result["status"] == "not_comparable"
    assert result["reason_code"] in {"reference_mismatch", "missing_axes"}
    assert result["change_deg"] is None


def test_history_cannot_close_an_existing_urgent_review():
    images, reports = pair("camera-roll")
    result = compare_pole_history(*images, *reports, repeatable_capture=True)
    previous = {"priority": "critical_review", "label": "Critical review", "team": "Asset engineering", "trace": []}
    current = {"priority": "routine", "label": "Routine review", "team": "Asset inspection", "trace": []}
    plan = history_plan(result, previous, current)
    assert plan["priority"] == "critical_review"
    assert "unresolved" in plan["reason"]


@pytest.mark.parametrize("value", ["last week", "2026-10-01T12:00:00", "2026-99-99T12:00:00Z"])
def test_observation_date_requires_an_explicit_valid_timezone(value):
    with pytest.raises(ValueError):
        observation_time(value)


def test_observation_dates_are_normalized_and_future_dates_are_rejected():
    assert observation_time("2026-10-01T05:00:00-07:00") == "2026-10-01T12:00:00+00:00"
    with pytest.raises(ValueError):
        observation_time((datetime.now(timezone.utc) + timedelta(days=1)).isoformat())


@pytest.fixture
def client(tmp_path, monkeypatch):
    from spanwitness import app as module
    from spanwitness.store import Store
    monkeypatch.setattr(module, "store", Store(tmp_path))
    monkeypatch.delenv("SPANWITNESS_ACCESS_CODE", raising=False)
    with TestClient(module.app) as client:
        yield client


def upload(client, view, *, case="alignment-change", asset="Pole 27", observed_at=None):
    image, geometry = render_history_scene(case, view)
    data = {"asset_id": asset, "source_kind": "synthetic", "span": "null",
        "pole": json.dumps(geometry["pole"]), "vertical_reference": json.dumps(geometry["vertical_reference"]),
        "location_label": "Controlled scene"}
    if observed_at is not None:
        data["observed_at"] = observed_at
    response = client.post("/api/analyze", data=data, files={"image": ("history.jpg", encode_image(image), "image/jpeg")})
    assert response.status_code == 200, response.text
    return response.json()


def test_history_comparison_export_review_and_persistence(client, monkeypatch):
    baseline = upload(client, "baseline", observed_at="2026-10-01T12:00:00Z")
    current = upload(client, "current", observed_at="2026-10-08T12:00:00Z")
    assert client.get("/api/assets").json()["assets"][0]["observation_count"] == 2
    response = client.post("/api/history/compare", json={"baseline_id": baseline["id"], "current_id": current["id"], "repeatable_capture": True})
    assert response.status_code == 200, response.text
    record = response.json()
    assert record["comparison"]["status"] == "change_detected"
    assert record["plan"]["priority"] == "major"
    assert record["baseline"]["input_sha256"] == baseline["input_sha256"]
    assert client.get(record["export_url"]).json() == record
    from spanwitness import app as module
    from spanwitness.store import Store
    monkeypatch.setattr(module, "store", Store(module.store.directory))
    history = client.get("/api/assets/history", params={"asset_id": "Pole 27"}).json()
    assert [item["id"] for item in history["records"]] == [current["id"], baseline["id"]]
    assert history["comparisons"][0]["id"] == record["id"]
    ticket = {"observation_id": current["id"], "comparison_id": record["id"], "reviewer": "Demo QA",
              "note": "Controlled test only. Review the change evidence.", "confirm_provisional": False}
    assert client.post("/api/tickets", json=ticket).status_code == 400
    ticket["confirm_provisional"] = True
    saved = client.post("/api/tickets", json=ticket).json()
    assert saved["priority"] == "Major review" and saved["evidence_url"] == record["export_url"]
    assert client.post("/api/tickets", json=ticket).json()["id"] == saved["id"]
    assert len(client.get("/api/tickets").json()) == 1
    ticket["observation_id"] = baseline["id"]
    assert client.post("/api/tickets", json=ticket).status_code == 400


def test_saved_date_is_not_used_as_a_capture_date(client):
    baseline = upload(client, "baseline")
    current = upload(client, "current", observed_at="2026-10-08T12:00:00Z")
    assert baseline["observed_at"] is None and baseline["observation_time_source"] == "unknown"
    response = client.post("/api/history/compare", json={"baseline_id": baseline["id"], "current_id": current["id"], "repeatable_capture": True})
    assert response.status_code == 400 and "dates" in response.json()["detail"]


def test_history_rejects_reversed_dates_and_different_asset_ids(client):
    baseline = upload(client, "baseline", observed_at="2026-10-01T12:00:00Z")
    current = upload(client, "current", observed_at="2026-10-08T12:00:00Z")
    other = upload(client, "current", asset="Pole 28", observed_at="2026-10-08T12:00:00Z")
    for a, b in [(current, baseline), (baseline, other), (baseline, baseline)]:
        assert client.post("/api/history/compare", json={"baseline_id": a["id"], "current_id": b["id"], "repeatable_capture": True}).status_code == 400
