"""Verify the deployed API, private access and durable evidence. No secrets in output."""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import uuid

import boto3

WORKSPACE = Path(__file__).resolve().parents[2]


def main():
    receipt = json.loads((WORKSPACE / "deployment-receipt.json").read_text())
    session = boto3.Session(region_name=receipt["region"])
    stacks = session.client("cloudformation").describe_stacks(StackName=receipt["stack_name"])["Stacks"]
    stack = stacks[0]
    if stack["StackStatus"] not in {"CREATE_COMPLETE", "UPDATE_COMPLETE"}:
        raise RuntimeError("The application stack has not completed deployment.")
    outputs = {entry["OutputKey"]: entry["OutputValue"] for entry in stack["Outputs"]}
    origin = outputs["PreviewUrl"]
    if not urlparse(origin).hostname.endswith(f".execute-api.{receipt['region']}.amazonaws.com"):
        raise RuntimeError("Unexpected preview destination; credentials were not sent.")
    code = session.client("ssm").get_parameter(Name=receipt["preview_access_parameter"], WithDecryption=True)["Parameter"]["Value"]
    authorization = "Basic " + base64.b64encode(f"judge:{code}".encode()).decode()
    calls = []
    last_write = [0.0]

    def get(path, *, authenticated=True, data=None, content_type=None):
        headers = {"Authorization": authorization} if authenticated else {}
        if content_type:
            headers["Content-Type"] = content_type
        start = time.perf_counter()
        request = Request(origin + path, data=data, headers=headers)
        with urlopen(request, timeout=45) as response:
            body = response.read()
            calls.append({"path": path, "status": response.status, "elapsed_ms": round((time.perf_counter() - start) * 1000, 1)})
            return body, response.headers

    def post_image(image, points, asset, reference="", geometry=None, observed_at=""):
        boundary = "SpanWitness" + uuid.uuid4().hex
        parts = []
        fields = {"span": json.dumps(points), "asset_id": asset, "source_kind": "synthetic", "reference_id": reference}
        if geometry:
            fields.update(pole=json.dumps(geometry["pole"]), vertical_reference=json.dumps(geometry["vertical_reference"]), observed_at=observed_at)
        for key, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="fixture.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + image + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        time.sleep(max(0, 1.05 - (time.monotonic() - last_write[0])))
        last_write[0] = time.monotonic()
        body, _ = get("/api/analyze", data=b"".join(parts), content_type=f"multipart/form-data; boundary={boundary}")
        return json.loads(body)

    try:
        get("/api/health", authenticated=False)
    except HTTPError as error:
        assert error.code == 401
        calls.append({"path": "/api/health", "authenticated": False, "status": 401})
    else:
        raise RuntimeError("The private preview unexpectedly allowed an unauthenticated request.")
    health = json.loads(get("/api/health")[0])
    assert health["opencv"].startswith("5.") and health["storage"] == "aws_s3_dynamodb", health
    html = get("/")[0]
    assert html == (WORKSPACE / "spanwitness/static/index.html").read_bytes()
    assets = {}
    for name in ["app.js", "history.js", "style.css"]:
        body = get("/static/" + name)[0]
        assert body == (WORKSPACE / "spanwitness/static" / name).read_bytes()
        assets[name] = hashlib.sha256(body).hexdigest()
    examples = json.loads(get("/api/examples")[0])
    example = {item["id"]: item for item in examples}
    image = get("/api/examples/gap/image")[0]
    gap = post_image(image, example["gap"]["span"], "AWS demo smoke: gap")
    assert gap["plan"]["priority"] == "critical_review"
    stored = get(gap["image_url"])[0]
    assert hashlib.sha256(stored).hexdigest() == gap["stored_image_sha256"]
    assert get(gap["overlay_url"])[0].startswith(b"\xff\xd8")
    exported = json.loads(get(f"/api/observations/{gap['id']}/export")[0])
    assert exported["id"] == gap["id"] and exported["input_sha256"] == gap["input_sha256"]
    first_image = get("/api/examples/perspective/image?view=1")[0]
    first = post_image(first_image, example["perspective"]["span"], "AWS demo smoke: viewpoint")
    assert first["plan"]["priority"] == "major"
    # The write route is intentionally limited to one request per second.
    time.sleep(1.1)
    second_image = get("/api/examples/perspective/image?view=2")[0]
    second = post_image(second_image, example["perspective"]["second_span"], "AWS demo smoke: viewpoint", first["id"])
    assert second["comparison"]["status"] == "projection_sensitive"
    assert second["plan"]["priority"] == "moderate"
    saved = json.loads(get(f"/api/observations/{second['id']}")[0])
    assert saved["reference_id"] == first["id"]
    history_examples = {item["id"]: item for item in json.loads(get("/api/history/examples")[0])}
    history_checks = []
    for case, expected in [("alignment-change", "change_detected"), ("camera-roll", "no_material_change")]:
        fixture = history_examples[case]
        records = []
        for view in ["baseline", "current"]:
            sample = fixture["views"][view]
            records.append(post_image(get(sample["image_url"])[0], None, f"AWS history smoke: {case}",
                geometry=sample["geometry"], observed_at=sample["observed_at"]))
        comparison = json.loads(get("/api/history/compare", data=json.dumps({"baseline_id": records[0]["id"],
            "current_id": records[1]["id"], "repeatable_capture": True, "capture_setup_source": "controlled_fixture"}).encode(), content_type="application/json")[0])
        assert comparison["comparison"]["status"] == expected
        assert comparison["comparison"]["capture_setup"] == "fixture_declared_repeatable_view"
        expected_angle = 5 if case == "alignment-change" else 0
        assert abs(comparison["comparison"]["change_deg"] - expected_angle) < .5
        exported = json.loads(get(comparison["export_url"])[0])
        assert exported["id"] == comparison["id"] and exported["baseline"]["input_sha256"] == records[0]["input_sha256"]
        # The history uses the existing eventually-consistent DynamoDB index.
        from urllib.parse import quote
        for attempt in range(12):
            history = json.loads(get("/api/assets/history?asset_id=" + quote(records[0]["asset_id"]))[0])
            if comparison["id"] in {entry["id"] for entry in history["comparisons"]} and all(record["id"] in {entry["id"] for entry in history["records"]} for record in records):
                break
            time.sleep(.5)
        else:
            raise RuntimeError("The saved comparison did not appear in the history index within the verification window.")
        history_checks.append({"case": case, "status": comparison["comparison"]["status"], "change_deg": comparison["comparison"]["change_deg"],
            "comparison_id": comparison["id"], "baseline_id": records[0]["id"], "current_id": records[1]["id"]})
    result = {"status": "passed", "verified_at": datetime.now(timezone.utc).isoformat(), "preview_url": origin,
              "health": health, "assets_sha256": assets, "observations": {"gap": gap["id"], "first_view": first["id"], "second_view": second["id"]},
              "second_view_status": second["comparison"]["status"], "history": history_checks,
              "checks": ["unauthenticated request rejected", "real OpenCV 5 on Lambda", "S3 image and overlay readback", "DynamoDB record readback", "evidence export", "measurement-driven second-view decision", "frontend assets match tested source", "pole history change and camera-roll control", "comparison export and DynamoDB history persistence"],
              "calls": calls, "limits": "Synthetic workflow verification. No field-accuracy score or browser-login verification is implied."}
    (WORKSPACE / "live-smoke-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
