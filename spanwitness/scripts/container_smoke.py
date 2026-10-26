"""Exercise real Lambda HTTP events in the Linux image, without AWS calls."""
import base64
import json
from types import SimpleNamespace

import httpx

from spanwitness.examples import render_scene
from spanwitness.lambda_handler import handler
from spanwitness.vision import encode_image


def invoke(path, method="GET", headers=None, body=b""):
    event = {"version": "2.0", "routeKey": "$default", "rawPath": path, "rawQueryString": "",
             "headers": {"host": "localhost", "x-forwarded-proto": "https", **(headers or {})},
             "requestContext": {"http": {"method": method, "path": path, "sourceIp": "127.0.0.1", "protocol": "HTTP/1.1"}},
             "body": base64.b64encode(body).decode(), "isBase64Encoded": True}
    response = handler(event, SimpleNamespace(aws_request_id="container-smoke"))
    assert response["statusCode"] == 200, response
    return response


def main():
    health = json.loads(invoke("/api/health")["body"])
    assert health["opencv"].startswith("5.")
    frame, points = render_scene("gap")
    request = httpx.Request("POST", "http://localhost/api/analyze", data={"span": json.dumps(points), "source_kind": "synthetic"},
                            files={"image": ("fixture.jpg", encode_image(frame), "image/jpeg")})
    response = invoke("/api/analyze", "POST", {"content-type": request.headers["content-type"]}, request.read())
    record = json.loads(response["body"])
    assert record["plan"]["priority"] == "critical_review"
    image_response = invoke(record["image_url"])
    assert image_response["isBase64Encoded"]
    assert base64.b64decode(image_response["body"]).startswith(b"\xff\xd8")
    assert json.loads(invoke(f"/api/observations/{record['id']}/export")["body"])["input_sha256"] == record["input_sha256"]
    print(json.dumps({"result": "passed", "runtime": health, "decision": record["plan"]["priority"],
                      "checks": ["Lambda event adapter", "OpenCV gap analysis", "multipart image", "binary JPEG response", "evidence export"],
                      "aws_calls": False}))


if __name__ == "__main__":
    main()
