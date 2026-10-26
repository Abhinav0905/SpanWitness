"""Prepare a local-image SAM template after a Docker BuildKit build.

Run with the isolated SAM CLI environment. Does not contact AWS or deploy.
"""
import json
from pathlib import Path

from samcli.yamlhelper import yaml_parse

root = Path(__file__).resolve().parents[1]
template = yaml_parse((root / "template.yaml").read_text())
function = template["Resources"]["InspectionFunction"]
function.pop("Metadata", None)
function["Properties"]["ImageUri"] = "spanwitness:local"
destination = root / "artifacts" / "deployment-template.json"
destination.parent.mkdir(exist_ok=True)
destination.write_text(json.dumps(template, indent=2) + "\n")
print(destination)
