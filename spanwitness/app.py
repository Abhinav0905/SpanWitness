"""Local inspection API and interface. No messages or dispatch orders are sent."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import secrets
import base64
import uuid
from typing import Literal

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .examples import EXAMPLES, normalized_span, render_scene, pole_annotations
from .policy import plan_review
from .store import Store
from .vision import analyze, compare_views, decode_image, encode_image
from .weather import nws_context
from .history import observation_time, compare_pole_history, history_plan
from .history_examples import HISTORY_EXAMPLES, render_history_scene

ROOT = Path(__file__).parent
store = Store(Path(os.environ.get("SPANWITNESS_DATA", str(ROOT / "data"))))
if os.environ.get("SPANWITNESS_BUCKET"):
    from .aws_store import AWSStore
    store = AWSStore(os.environ["SPANWITNESS_BUCKET"], os.environ["SPANWITNESS_TABLE"])
app = FastAPI(title="SpanWitness", version=__version__)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.middleware("http")
async def preview_access(request, call_next):
    code = os.environ.get("SPANWITNESS_ACCESS_CODE")
    if code:
        try:
            scheme, encoded = request.headers.get("Authorization", "").split(" ", 1)
            username, password = base64.b64decode(encoded, validate=True).decode().split(":", 1)
            valid = scheme.lower() == "basic" and username == "judge" and secrets.compare_digest(password.encode(), code.encode())
        except (ValueError, UnicodeError):
            valid = False
        if not valid:
            return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="SpanWitness preview"'})
    return await call_next(request)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_or_404(identifier: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", identifier):
        raise HTTPException(404, "Observation not found.")
    record = store.get("observations", identifier)
    if not record:
        raise HTTPException(404, "Observation not found.")
    return record


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "app_version": __version__, "opencv": cv2.__version__,
            "storage": store.backend, "dispatch": "review_queue_only", "model": "classical_cv_with_bounded_policy",
            "runtime": {"compute": "aws_lambda" if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else "local",
                        "function": os.environ.get("AWS_LAMBDA_FUNCTION_NAME"),
                        "region": os.environ.get("AWS_REGION"), "python": platform.python_version()}}


@app.get("/api/examples")
def examples():
    output = []
    for example in EXAMPLES:
        item = dict(example)
        item["image_url"] = f"/api/examples/{item['id']}/image"
        item["span"] = normalized_span(item["id"])
        item["geometry"] = pole_annotations(item["id"])
        if item["second_view"]:
            item["second_span"] = normalized_span(item["id"], 2)
        output.append(item)
    return output


@app.get("/api/examples/{example_id}/image")
def example_image(example_id: str, view: int = 1):
    example = next((item for item in EXAMPLES if item["id"] == example_id), None)
    if not example or view not in {1, 2}:
        raise HTTPException(404, "Example not found.")
    if example["kind"] == "public_image":
        return FileResponse(ROOT / "static" / "samples" / f"{example_id}.jpg")
    image, _ = render_scene(example_id, view)
    return Response(encode_image(image), media_type="image/jpeg")


@app.get("/api/weather")
async def weather(latitude: float, longitude: float):
    try:
        return await nws_context(latitude, longitude)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.post("/api/analyze")
async def inspect_image(image: UploadFile = File(...), span: str = Form("null"),
                        asset_id: str = Form("Pole SW-27", max_length=80),
                        reference_id: str = Form(""), source_kind: str = Form("user_upload"),
                        weather_context: str = Form("null"), latitude: float | None = Form(None),
                        longitude: float | None = Form(None), pole: str = Form("null"),
                        vertical_reference: str = Form("null"), observed_at: str = Form(""),
                        location_label: str = Form("", max_length=120)):
    raw = await image.read(4_000_001)
    if len(raw) > 4_000_000:
        raise HTTPException(400, "Choose an image smaller than 4 MB. The browser resizes phone photos before upload.")
    if (latitude is None) != (longitude is None):
        raise HTTPException(400, "Provide both latitude and longitude.")
    try:
        capture_time = observation_time(observed_at)
        points = json.loads(span)
        context = json.loads(weather_context)
        if context is not None and not isinstance(context, dict):
            raise ValueError("Invalid weather context.")
        # Client-provided context can be an example, not an authenticated official alert.
        if context:
            context["source_kind"] = "operator_supplied_context"
            context["status"] = "operator_supplied"
        frame = decode_image(raw)
        report, overlay, _ = analyze(frame, points, json.loads(pole), json.loads(vertical_reference))
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, cv2.error) as error:
        raise HTTPException(400, str(error) if not isinstance(error, cv2.error) else "This image could not be analyzed.") from error
    reference = record_or_404(reference_id) if reference_id else None
    if reference and reference["asset_id"] != asset_id.strip():
        raise HTTPException(400, "Both observations must refer to the same asset ID.")
    comparison = None
    if latitude is not None and longitude is not None:
        try:
            context = await nws_context(latitude, longitude)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
    if reference:
        previous = decode_image(store.read_image(f"{reference_id}.jpg"))
        comparison = compare_views(previous, frame, reference["report"], report)
    plan = plan_review(report, context, comparison, reference["plan"] if reference else None)
    identifier = uuid.uuid4().hex
    encoded = encode_image(frame)
    store.write_image(f"{identifier}.jpg", encoded)
    store.write_image(f"{identifier}-overlay.jpg", encode_image(overlay))
    input_digest = hashlib.sha256(raw).hexdigest()
    credits = json.loads((ROOT / "static" / "samples" / "ATTRIBUTION.json").read_text())
    attribution = next((credit for credit in credits if credit["sha256"] == input_digest), None)
    record = {"id": identifier, "created_at": now(), "asset_id": asset_id.strip() or "Unassigned asset",
              "observed_at": capture_time, "observation_time_source": "operator_supplied" if capture_time else "unknown",
              "location_label": location_label.strip(), "location_source": "operator_supplied" if location_label.strip() else "unknown",
              "source_kind": source_kind if source_kind in {"synthetic", "public_image", "user_upload", "camera"} else "user_upload",
              "source_provenance": "Client-declared source category; not a camera-liveness attestation.",
              "input_sha256": input_digest, "source_attribution": attribution,
              "stored_image_sha256": hashlib.sha256(encoded).hexdigest(),
              "report": report, "plan": plan, "comparison": comparison, "weather": context or {"status": "unknown"},
              "reference_id": reference_id or None, "image_url": f"/api/observations/{identifier}/image",
              "overlay_url": f"/api/observations/{identifier}/image?overlay=true"}
    store.save("observations", record)
    return record


@app.get("/api/observations")
def observations(q: str = ""):
    records = store.list("observations", 100)
    query = q.lower().strip()
    filters = {}
    priority_words = {"critical": "critical_review", "urgent": "critical_review", "major": "major",
                      "moderate": "moderate", "routine": "routine", "unassessed": "unassessed"}
    for word, priority in priority_words.items():
        if re.search(r"\b" + word + r"\b", query):
            filters["priority"] = priority
    if any(word in query for word in ["vegetation", "grass", "tree"]):
        filters["finding"] = "vegetation"
    if any(word in query for word in ["gap", "broken", "conductor"]):
        filters["finding"] = "conductor"
    if any(word in query for word in ["lean", "alignment", "tilt"]):
        filters["finding"] = "alignment"
    selected = []
    for record in records:
        if filters.get("priority") and record["plan"]["priority"] != filters["priority"]:
            continue
        codes = " ".join(finding["code"] for finding in record["report"]["findings"])
        if filters.get("finding") == "vegetation" and not any(word in codes for word in ["vegetation", "ground_cover"]):
            continue
        if filters.get("finding") == "conductor" and "conductor" not in codes:
            continue
        if filters.get("finding") == "alignment" and "pole_alignment_candidate" not in codes:
            continue
        if query and not filters and query not in record["asset_id"].lower():
            continue
        selected.append(record)
    return {"records": selected, "filters": filters, "parser": "bounded_keyword_filters", "total": len(selected)}


@app.get("/api/observations/{identifier}")
def observation(identifier: str):
    return record_or_404(identifier)


@app.get("/api/observations/{identifier}/image")
def observation_image(identifier: str, overlay: bool = False):
    record_or_404(identifier)
    return Response(store.read_image(f"{identifier}{'-overlay' if overlay else ''}.jpg"), media_type="image/jpeg")


class TicketRequest(BaseModel):
    observation_id: str
    reviewer: str = Field(min_length=1, max_length=80)
    note: str = Field(min_length=1, max_length=1000)
    confirm_provisional: bool
    comparison_id: str | None = None


@app.post("/api/tickets")
def create_ticket(request: TicketRequest):
    observation = record_or_404(request.observation_id)
    evidence = observation
    if request.comparison_id:
        evidence = comparison_or_404(request.comparison_id)
        if evidence["current_id"] != observation["id"]:
            raise HTTPException(400, "The review must refer to this comparison's current observation.")
    if not request.confirm_provisional:
        raise HTTPException(400, "A reviewer must confirm the provisional priority.")
    if not request.reviewer.strip() or not request.note.strip():
        raise HTTPException(400, "Enter a reviewer name and review note.")
    ticket_id = evidence["id"]
    existing = store.get("tickets", ticket_id)
    if existing:
        return existing
    ticket = {"id": ticket_id, "created_at": now(), "observation_id": observation["id"],
              "comparison_id": request.comparison_id, "asset_id": observation["asset_id"], "priority": evidence["plan"]["label"],
              "team": evidence["plan"]["team"], "status": "queued_for_review",
              "reviewer": request.reviewer.strip(), "note": request.note.strip(),
              "action": evidence["plan"]["action"], "input_sha256": observation["input_sha256"],
              "evidence_url": f"/api/history/comparisons/{ticket_id}/export" if request.comparison_id else f"/api/observations/{observation['id']}/export",
              "delivery": "Application review queue. No external message or dispatch was sent."}
    try:
        store.save("tickets", ticket)
    except Exception:
        # A concurrent retry may have saved the same observation's request.
        existing = store.get("tickets", ticket_id)
        if existing:
            return existing
        raise
    return ticket


@app.get("/api/tickets")
def tickets():
    return store.list("tickets")


@app.get("/api/observations/{identifier}/export")
def export_observation(identifier: str):
    record = record_or_404(identifier)
    return JSONResponse(record, headers={"Content-Disposition": f'attachment; filename="spanwitness-{identifier[:8]}.json"'})


def comparison_or_404(identifier: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", identifier):
        raise HTTPException(404, "Comparison not found.")
    record = store.get("comparisons", identifier)
    if not record:
        raise HTTPException(404, "Comparison not found.")
    return record


@app.get("/api/assets")
def assets():
    records = store.list("observations", 100)
    grouped = {}
    for record in records:
        item = grouped.setdefault(record["asset_id"], {"asset_id": record["asset_id"], "observation_count": 0,
            "latest_recorded_at": record["created_at"], "location_label": record.get("location_label", "")})
        item["observation_count"] += 1
        if not item["location_label"]:
            item["location_label"] = record.get("location_label", "")
    return {"assets": list(grouped.values()), "scope": "newest_100_observations", "observations_in_window": len(records)}


@app.get("/api/assets/history")
def asset_history(asset_id: str):
    records = [record for record in store.list("observations", 100) if record["asset_id"] == asset_id]
    records.sort(key=lambda record: record.get("observed_at") or record["created_at"], reverse=True)
    comparisons = [record for record in store.list("comparisons", 100) if record["asset_id"] == asset_id]
    return {"asset_id": asset_id, "records": records, "comparisons": comparisons,
            "scope": "newest_100_observations_and_100_comparisons", "identity": "operator_assigned_asset_id"}


class HistoryRequest(BaseModel):
    baseline_id: str
    current_id: str
    repeatable_capture: bool = False
    capture_setup_source: Literal["operator_confirmation", "controlled_fixture"] = "operator_confirmation"


@app.post("/api/history/compare")
def compare_history(request: HistoryRequest):
    baseline, current = record_or_404(request.baseline_id), record_or_404(request.current_id)
    if baseline["id"] == current["id"]:
        raise HTTPException(400, "Choose two separate observations.")
    if baseline["asset_id"] != current["asset_id"]:
        raise HTTPException(400, "Choose observations of the same asset ID.")
    if request.capture_setup_source == "controlled_fixture" and any(record["source_kind"] != "synthetic" for record in [baseline, current]):
        raise HTTPException(400, "Controlled-fixture provenance is only available for synthetic observations.")
    if not baseline.get("observed_at") or not current.get("observed_at"):
        raise HTTPException(400, "Both observations need supplied observation dates. A saved-record date is not a photo capture date.")
    if baseline["observed_at"] >= current["observed_at"]:
        raise HTTPException(400, "The current observation must be later than the baseline.")
    first = decode_image(store.read_image(f"{baseline['id']}.jpg"))
    second = decode_image(store.read_image(f"{current['id']}.jpg"))
    result = compare_pole_history(first, second, baseline["report"], current["report"],
        repeatable_capture=request.repeatable_capture, same_file=baseline["input_sha256"] == current["input_sha256"])
    result["capture_setup_source"] = request.capture_setup_source
    if request.capture_setup_source == "controlled_fixture" and request.repeatable_capture:
        result["capture_setup"] = "fixture_declared_repeatable_view"
    identifier = uuid.uuid4().hex
    record = {"id": identifier, "created_at": now(), "asset_id": current["asset_id"],
        "baseline_id": baseline["id"], "current_id": current["id"], "baseline": baseline, "current": current,
        "comparison": result, "plan": history_plan(result, baseline["plan"], current["plan"]),
        "provenance": "Asset identity, observation times, location and capture setup are operator-supplied. Background correspondence is supporting evidence, not a camera-pose or 3D guarantee.",
        "export_url": f"/api/history/comparisons/{identifier}/export"}
    store.save("comparisons", record)
    return record


@app.get("/api/history/comparisons/{identifier}/export")
def export_comparison(identifier: str):
    return JSONResponse(comparison_or_404(identifier), headers={"Content-Disposition": f'attachment; filename="spanwitness-history-{identifier[:8]}.json"'})


@app.get("/api/history/examples")
def history_examples():
    output = []
    for example in HISTORY_EXAMPLES:
        item = dict(example)
        item["kind"] = "synthetic"
        item["asset_id"] = f"Demo pole - {example['id']}"
        item["views"] = {}
        for view, stamp in [("baseline", "2026-10-01T12:00:00+00:00"), ("current", "2026-10-08T12:00:00+00:00")]:
            _, geometry = render_history_scene(example["id"], view)
            item["views"][view] = {"image_url": f"/api/history/examples/{example['id']}/image?view={view}",
                "geometry": geometry, "observed_at": stamp}
        output.append(item)
    return output


@app.get("/api/history/examples/{case}/image")
def history_example_image(case: str, view: str = "baseline"):
    try:
        image, _ = render_history_scene(case, view)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    return Response(encode_image(image), media_type="image/jpeg")
