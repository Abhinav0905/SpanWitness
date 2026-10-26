"""Download a small, revision-pinned PD-Defect validation sample.

No labels are passed to perception. Raw images stay in the ignored data directory.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
from io import BytesIO, StringIO
import json
from pathlib import Path
import time
from urllib.parse import quote
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "EPDCL/pd-defect"
REVISION = "b9c64b2f9615ef5ade71fceade7d9d31b0dc9416"
RESOLVE = f"https://huggingface.co/datasets/{REPOSITORY}/resolve/{REVISION}/"
DESTINATION = ROOT / "data" / "public_datasets" / "pd_defect"
CATALOG = ROOT / "datasets" / "pd_defect"


def request_bytes(url: str) -> bytes:
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "SpanWitness-data-intake/0.1"}), timeout=45) as response:
                data = response.read(25_000_001)
            if len(data) > 25_000_000:
                raise ValueError("Public sample file exceeds the 25 MB intake limit.")
            return data
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Download failed.")


def remote(path: str) -> bytes:
    return request_bytes(RESOLVE + quote(path, safe="/"))


def inventory(path: str) -> list[dict]:
    url = f"https://huggingface.co/api/datasets/{REPOSITORY}/tree/{REVISION}/{path}?recursive=false&limit=1000"
    return json.loads(request_bytes(url))


def choose(rows: list[dict], count: int) -> list[dict]:
    # Spread filenames without inspecting image contents or model predictions.
    return sorted(rows, key=lambda row: hashlib.sha256(row["path"].encode()).hexdigest())[:count]


def download(item: dict) -> dict:
    path = Path(item["path"])
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Invalid dataset path.")
    destination = DESTINATION / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = destination.read_bytes() if destination.exists() else remote(item["path"])
    with Image.open(BytesIO(data)) as image:
        image.verify()
    with Image.open(BytesIO(data)) as image:
        width, height = image.size
    destination.write_bytes(data)
    return {**item, "url": RESOLVE + quote(item["path"], safe="/"), "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data), "width": width, "height": height, "local_path": str(destination.relative_to(ROOT)),
            "license": "CC BY 4.0", "privacy_review": "not_cleared_for_public_display"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-pole-class", type=int, default=8)
    parser.add_argument("--per-vegetation-class", type=int, default=6)
    options = parser.parse_args()
    if not 1 <= options.per_pole_class <= 50 or not 1 <= options.per_vegetation_class <= 50:
        parser.error("Select between 1 and 50 images per class.")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    CATALOG.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for path in ["README.md", "pole_lean_assessment/README.md", "vegetation_conductor/README.md",
                 "vegetation_conductor/GT_ValidationSet.csv", "vegetation_conductor/valid/_annotations.coco.json"]:
        data = remote(path)
        target = DESTINATION / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        metadata[path] = {"url": RESOLVE + path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    selected = []
    for label in ["Leaned", "Straight", "Rejected"]:
        folder = f"pole_lean_assessment/classification/val/{label}"
        rows = [item for item in inventory(folder) if item["type"] == "file" and item["path"].lower().endswith(".jpg")]
        selected += [{"path": item["path"], "module": "pole_lean_classification", "split": "val", "publisher_label": label}
                     for item in choose(rows, options.per_pole_class)]
    labels = list(csv.DictReader(StringIO((DESTINATION / "vegetation_conductor/GT_ValidationSet.csv").read_text(encoding="utf-8-sig"))))
    for label in ["Risky", "Safe"]:
        rows = [{"path": f"vegetation_conductor/valid/{row['ID']}", "module": "vegetation_conductor", "split": "valid", "publisher_label": label}
                for row in labels if row["Ground_Truth"] == label]
        selected += choose(rows, options.per_vegetation_class)
    with ThreadPoolExecutor(max_workers=4) as pool:
        samples = list(pool.map(download, selected))
    coco = json.loads((DESTINATION / "vegetation_conductor/valid/_annotations.coco.json").read_bytes())
    wanted = {Path(item["path"]).name for item in samples if item["module"] == "vegetation_conductor"}
    images = [image for image in coco["images"] if image["file_name"] in wanted]
    image_ids = {image["id"] for image in images}
    subset = {"images": images, "annotations": [a for a in coco["annotations"] if a["image_id"] in image_ids], "categories": coco["categories"]}
    (CATALOG / "vegetation-sample-annotations.json").write_text(json.dumps(subset, indent=2) + "\n")
    counts = Counter(f"{s['module']}/{s['publisher_label']}" for s in samples)
    unique = len({s["sha256"] for s in samples})
    manifest = {"source": "PD-Defect", "repository": REPOSITORY, "revision": REVISION,
                "doi": "10.6084/m9.figshare.34329402", "source_url": f"https://huggingface.co/datasets/{REPOSITORY}",
                "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "attribution": "Masabathula, Sampath Balaji; Vanapalli, Srija; Kanchi, Gangadhar; V.A.N, Sreenivasa Rao; V, Vijaya Lalitha; Chilamkurthy, Sasank (2026). PD-Defect.",
                "downloaded_at": datetime.now(timezone.utc).isoformat(), "sample_count": len(samples), "unique_sha256_count": unique,
                "bytes": sum(s["bytes"] for s in samples), "class_counts": dict(counts), "metadata": metadata, "samples": samples,
                "selection": "SHA-256 path ordering; balanced small validation sample. No training or test split was downloaded.",
                "limits": ["Publisher labels are reference annotations, not SpanWitness predictions or certified physical condition.",
                           "Risky/Safe labels do not supply metric clearance or fire probability.",
                           "Raw files are local and excluded from the source archive. Review visible people and identifiers before public display.",
                           "Do not tune on this sample and then describe it as held-out test data."]}
    (CATALOG / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({key: manifest[key] for key in ["sample_count", "unique_sha256_count", "bytes", "class_counts", "revision"]}))


if __name__ == "__main__":
    main()
