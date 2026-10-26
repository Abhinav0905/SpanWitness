"""Fetch the publisher's original pole train/validation splits. Test is opt-in."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from datetime import datetime, timezone
import argparse
import json
import shutil

from .fetch_public_data import CATALOG, DESTINATION, REVISION, download, inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-test", action="store_true", help="Only after freezing the model and evaluation procedure.")
    args = parser.parse_args()
    selected = []
    for split in ["train", "val"] + (["test"] if args.include_test else []):
        for label in ["Leaned", "Rejected", "Straight"]:
            folder = f"pole_lean_assessment/classification/{split}/{label}"
            rows = [row for row in inventory(folder) if row["type"] == "file" and row["path"].lower().endswith(".jpg")]
            selected += [{"path": row["path"], "module": "pole_lean_classification", "split": split,
                          "publisher_label": label, "declared_bytes": row.get("size", 0)} for row in rows]
    required = sum(item["declared_bytes"] for item in selected if not (DESTINATION / item["path"]).exists())
    if required > 3_000_000_000 or shutil.disk_usage(DESTINATION).free < required + 5_000_000_000:
        raise RuntimeError("The intake would exceed its disk budget. No new files were downloaded.")
    print(json.dumps({"selected": len(selected), "estimated_new_bytes": required, "includes_test": args.include_test}), flush=True)
    samples = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(download, item) for item in selected]
        for future in as_completed(futures):
            samples.append(future.result())
            if len(samples) % 100 == 0:
                print(json.dumps({"downloaded": len(samples), "total": len(selected)}), flush=True)
    samples.sort(key=lambda item: item["path"])
    train_hashes = {item["sha256"] for item in samples if item["split"] == "train"}
    overlaps = [item["path"] for item in samples if item["split"] != "train" and item["sha256"] in train_hashes]
    output = {"revision": REVISION, "generated_at": datetime.now(timezone.utc).isoformat(),
              "source": "https://huggingface.co/datasets/EPDCL/pd-defect", "license": "CC BY 4.0",
              "class_order": ["Leaned", "Rejected", "Straight"], "includes_test": args.include_test,
              "counts": dict(Counter(f"{item['split']}/{item['publisher_label']}" for item in samples)),
              "exact_train_overlap_paths": overlaps, "samples": samples}
    destination = CATALOG / ("pole-all-splits-manifest.json" if args.include_test else "pole-development-manifest.json")
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"result": "downloaded", "counts": output["counts"], "exact_train_overlap_count": len(overlaps)}), flush=True)


if __name__ == "__main__":
    main()
