"""Create a review archive without local uploads, records or credentials."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
workspace = root.parent
excluded = {"data", "artifacts", "__pycache__", ".pytest_cache", ".DS_Store", ".aws", "samconfig.toml"}
files = [path for path in root.rglob("*") if path.is_file() and not excluded.intersection(path.relative_to(root).parts)
         and not path.name.startswith(".env")]
files += [workspace / ".dockerignore", workspace / ".gitignore"]
destination = root / "artifacts"
destination.mkdir(exist_ok=True)
archive = destination / "SpanWitness-source.zip"
manifest = []
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(files):
        relative = path.relative_to(workspace).as_posix()
        data = path.read_bytes()
        manifest.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        bundle.writestr(relative, data)
    readme = b"# SpanWitness source\n\nStart with [the project README](spanwitness/README.md) for setup, tests, data rights and AWS deployment.\n\nThe archive includes the application, technical report, tests, data credits and AWS deployment scripts.\n"
    bundle.writestr("README.md", readme)
    manifest.append({"path": "README.md", "sha256": hashlib.sha256(readme).hexdigest(), "bytes": len(readme)})
    bundle.writestr("SOURCE_MANIFEST.json", json.dumps(manifest, indent=2))
receipt = {"archive": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
           "files": len(manifest), "bytes": archive.stat().st_size, "excludes": sorted(excluded),
           "status": "local_review_archive_not_submitted"}
(destination / "source-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
