"""Regression checks for decisions and failure handling, not field accuracy."""
import copy
import json
from io import BytesIO

import cv2
import numpy as np
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from spanwitness.examples import render_scene, pole_annotations
from spanwitness.policy import plan_review
from spanwitness.vision import analyze, compare_views, decode_image, encode_image


def observation(case, view=1, seed=23):
    frame, points = render_scene(case, view, seed)
    frame = decode_image(encode_image(frame))
    report, overlay, _ = analyze(frame, points)
    return frame, points, report, overlay


@pytest.mark.parametrize("seed", [23, 71, 208])
@pytest.mark.parametrize("case,expected", [
    ("perspective", "major"), ("persistent", "major"), ("gap", "critical_review"),
    ("cover", "moderate"), ("clear", "routine"), ("blur", "unassessed")
])
def test_controlled_screening_cases(case, expected, seed):
    frame, _, report, overlay = observation(case, seed=seed)
    assert plan_review(report)["priority"] == expected
    assert overlay.shape == frame.shape
    assert report["runtime"]["opencv"].startswith("5.")
    assert report["span"]["measurement_units"] == "image pixels; not physical clearance"


@pytest.mark.parametrize("case,status,priority", [
    ("perspective", "projection_sensitive", "moderate"),
    ("persistent", "overlap_persists", "major")
])
def test_second_view_changes_the_next_action(case, status, priority):
    first, _, report, _ = observation(case)
    second, _, followup, _ = observation(case, 2)
    comparison = compare_views(first, second, report, followup)
    assert comparison["status"] == status
    assert comparison["inliers"] >= 10
    assert plan_review(followup, comparison=comparison, prior_plan=plan_review(report))["priority"] == priority


def test_repeated_image_is_not_a_second_view():
    frame, _, report, _ = observation("perspective")
    assert compare_views(frame, frame.copy(), report, report)["status"] == "duplicate_view"


def test_same_background_with_different_span_does_not_resolve_finding():
    first, _, report, _ = observation("perspective")
    second, _, followup, _ = observation("perspective", 2)
    wrong_span = copy.deepcopy(followup)
    wrong_span["span"]["points"] = [[.1, .7], [.8, .7]]
    comparison = compare_views(first, second, report, wrong_span)
    assert comparison["status"] == "different_span"
    plan = plan_review(wrong_span, comparison=comparison, prior_plan=plan_review(report))
    assert plan["priority"] == "major"


def test_later_empty_frame_cannot_close_urgent_finding():
    _, _, urgent, _ = observation("gap")
    _, _, clear, _ = observation("clear")
    followup = plan_review(clear, comparison={"status": "no_persistent_projection"}, prior_plan=plan_review(urgent))
    assert followup["priority"] == "critical_review"
    assert any(step["tool"] == "retain_unresolved_finding" for step in followup["trace"])


def test_failed_comparison_cannot_overwrite_a_new_urgent_finding():
    _, _, earlier, _ = observation("perspective")
    _, _, urgent, _ = observation("gap")
    plan = plan_review(urgent, comparison={"status": "different_span"}, prior_plan=plan_review(earlier))
    assert plan["priority"] == "critical_review"


def test_blank_or_unrelated_image_needs_more_evidence():
    blank = np.full((400, 600, 3), 180, dtype=np.uint8)
    report, _, _ = analyze(blank)
    assert plan_review(report)["priority"] == "unassessed"


@pytest.mark.parametrize("case,expected", [("pole-lean", "major"), ("camera-roll", "routine")])
def test_pole_alignment_uses_a_reference_to_cancel_camera_roll(case, expected):
    image, _ = render_scene(case)
    axes = pole_annotations(case)
    report, _, _ = analyze(decode_image(encode_image(image)), None, axes["pole"], axes["vertical_reference"])
    alignment = report["pole_alignment"]
    assert alignment["usable"]
    assert plan_review(report)["priority"] == expected
    if case == "camera-roll":
        assert abs(alignment["pole"]["angle_from_image_vertical_deg"]) > 10
        assert abs(alignment["relative_angle_deg"]) < 1


def test_pole_without_reference_cannot_be_assigned_low_priority():
    image, _ = render_scene("pole-lean")
    report, _, _ = analyze(image, None, pole_annotations("pole-lean")["pole"])
    assert plan_review(report)["priority"] == "unassessed"


def test_weather_escalation_is_context_not_fire_probability():
    _, _, report, _ = observation("cover")
    assert plan_review(report, {"status": "unavailable"})["priority"] == "moderate"
    plan = plan_review(report, {"status": "available", "source_kind": "live_nws", "fire_weather_alert": True})
    assert plan["priority"] == "major"
    assert "no fire-spread probability" in plan["reason"]


def test_exif_rotation_is_applied_before_marking_coordinates():
    image = Image.new("RGB", (400, 200), "white")
    exif = image.getexif()
    exif[274] = 6
    output = BytesIO()
    image.save(output, "JPEG", exif=exif)
    assert decode_image(output.getvalue()).shape[:2] == (400, 200)


@pytest.fixture
def client(tmp_path, monkeypatch):
    from spanwitness import app as module
    from spanwitness.store import Store
    monkeypatch.setattr(module, "store", Store(tmp_path))
    monkeypatch.delenv("SPANWITNESS_ACCESS_CODE", raising=False)
    with TestClient(module.app) as client:
        yield client


def submit(client, case="perspective", **extra):
    frame, points = render_scene(case)
    return client.post("/api/analyze", files={"image": ("test.jpg", encode_image(frame), "image/jpeg")},
                       data={"span": json.dumps(points), "source_kind": "synthetic", "asset_id": "Test pole", **extra})


def test_evidence_roundtrip_search_and_human_review(client):
    response = submit(client, "gap")
    assert response.status_code == 200
    record = response.json()
    assert len(record["input_sha256"]) == 64
    assert client.get(record["image_url"]).headers["content-type"] == "image/jpeg"
    assert client.get(f"/api/observations/{record['id']}/export").json() == record
    result = client.get("/api/observations", params={"q": "critical conductor"}).json()
    assert [item["id"] for item in result["records"]] == [record["id"]]
    ticket = {"observation_id": record["id"], "reviewer": "Demo reviewer", "note": "Inspect marked gap", "confirm_provisional": False}
    assert client.post("/api/tickets", json=ticket).status_code == 400
    ticket["confirm_provisional"] = True
    first = client.post("/api/tickets", json=ticket).json()
    second = client.post("/api/tickets", json=ticket).json()
    assert first["id"] == second["id"]
    assert len(client.get("/api/tickets").json()) == 1
    assert "No external" in first["delivery"]


def test_invalid_upload_and_span_are_client_errors(client):
    assert client.post("/api/analyze", files={"image": ("bad.jpg", b"not an image")}).status_code == 400
    assert submit(client, span="[[0,0],[2,1]]").status_code == 400
    assert submit(client, span="{}").status_code == 400
    assert client.get("/api/observations/not-a-record").status_code == 404


def test_health_identifies_actual_compute_environment(client, monkeypatch):
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    assert client.get("/api/health").json()["runtime"]["compute"] == "local"
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "spanwitness-test-function")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    runtime = client.get("/api/health").json()["runtime"]
    assert runtime["compute"] == "aws_lambda"
    assert runtime["function"] == "spanwitness-test-function"
    assert runtime["region"] == "us-west-2"


def test_unresolved_pole_does_not_route_a_brown_wall_to_vegetation(client):
    example = next(item for item in client.get("/api/examples").json() if item["id"] == "field-warehouse")
    response = client.post("/api/analyze", files={"image": ("field.jpg", client.get(example["image_url"]).content, "image/jpeg")},
                           data={"source_kind": "public_image", "pole": json.dumps(example["geometry"]["pole"]),
                                 "vertical_reference": json.dumps(example["geometry"]["vertical_reference"])})
    record = response.json()
    assert record["plan"]["priority"] == "unassessed"
    assert record["plan"]["team"] == "Asset inspection"
    assert "pole" in record["plan"]["action"]
    assert "conductor" not in record["plan"]["action"]
    assert "ground_cover_candidate" not in {item["code"] for item in record["report"]["findings"]}
    assert record["source_attribution"]["license"] == "CC BY 4.0"


def test_followup_rejects_different_asset(client):
    record = submit(client).json()
    assert submit(client, reference_id=record["id"], asset_id="Another pole").status_code == 400


def test_private_preview_requires_access_code(client, monkeypatch):
    monkeypatch.setenv("SPANWITNESS_ACCESS_CODE", "a-test-code-that-is-long")
    assert client.get("/").status_code == 401
    assert client.get("/api/health", auth=("judge", "incorrect")).status_code == 401
    assert client.get("/api/health", auth=("judge", "a-test-code-that-is-long")).status_code == 200
