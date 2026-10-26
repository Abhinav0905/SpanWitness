"""Train one declared pole-appearance pilot, then export for OpenCV inference."""
from __future__ import annotations

from collections import Counter
from collections import OrderedDict
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import time

import cv2
import numpy as np
from PIL import Image, ImageOps
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights, resnet18, ResNet18_Weights

from spanwitness.model_input import letterbox_rgb, MEAN, STD

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ["Leaned", "Rejected", "Straight"]
CONFIG = {"seed": 42, "epochs": 8, "frozen_epochs": 2, "batch_size": 32,
          "head_lr": .001, "fine_tune_lr": .00015, "weight_decay": .0001, "abstain_below": .65,
          "input": "whole-image letterbox; RGB ImageNet normalization", "class_order": CLASSES,
          "architecture": "mobilenet_v3_small", "side": 224}


class Images(Dataset):
    def __init__(self, images, labels, augment=False):
        self.images, self.labels, self.augment = images, labels, augment

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, index):
        image = self.images[index].astype(np.float32) / 255
        if self.augment:
            if random.random() < .5:
                image = image[:, ::-1].copy()
            image = np.clip((image - .5) * random.uniform(.9, 1.1) + .5 + random.uniform(-.06, .06), 0, 1)
        image = np.ascontiguousarray(((image - MEAN) / STD).transpose(2, 0, 1))
        return torch.from_numpy(image), int(self.labels[index])


def metrics(labels, logits):
    predictions = logits.argmax(1)
    matrix = np.zeros((3, 3), dtype=int)
    for actual, predicted in zip(labels, predictions):
        matrix[int(actual), int(predicted)] += 1
    scores = []
    classes = {}
    for i, name in enumerate(CLASSES):
        precision = matrix[i, i] / max(1, matrix[:, i].sum())
        recall = matrix[i, i] / max(1, matrix[i].sum())
        f1 = 2 * precision * recall / max(1e-12, precision + recall)
        scores.append(f1)
        classes[name] = {"precision": round(float(precision), 4), "recall": round(float(recall), 4), "f1": round(float(f1), 4), "count": int(matrix[i].sum())}
    probabilities = np.exp(logits - logits.max(1, keepdims=True))
    probabilities /= probabilities.sum(1, keepdims=True)
    covered = probabilities.max(1) >= CONFIG["abstain_below"]
    usable = covered & (predictions != CLASSES.index("Rejected"))
    return {"accuracy": round(float((predictions == labels).mean()), 4), "macro_f1": round(float(np.mean(scores)), 4),
            "confusion_matrix": matrix.tolist(), "classes": classes, "coverage_at_065": round(float(covered.mean()), 4),
            "usable_assessment_coverage": round(float(usable.mean()), 4),
            "covered_accuracy": round(float((predictions[covered] == labels[covered]).mean()), 4) if covered.any() else None}


def load_data(manifest):
    cache_dir = ROOT / "data" / "training"
    cache_dir.mkdir(exist_ok=True)
    fingerprint = hashlib.sha256(json.dumps({"side": CONFIG["side"], "samples": [(x["path"], x["sha256"]) for x in manifest["samples"]]}, sort_keys=True).encode()).hexdigest()[:16]
    cache = cache_dir / f"pole-images-{fingerprint}.npz"
    samples = manifest["samples"]
    if cache.exists():
        stored = np.load(cache)
        return stored["images"], stored["labels"], samples
    images, labels = [], []
    for index, sample in enumerate(samples):
        path = ROOT / sample["local_path"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sample["sha256"]:
            raise ValueError(f"Source hash mismatch: {sample['path']}")
        with Image.open(path) as picture:
            rgb = np.asarray(ImageOps.exif_transpose(picture).convert("RGB"))
        images.append(letterbox_rgb(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), CONFIG["side"]))
        labels.append(CLASSES.index(sample["publisher_label"]))
        if (index + 1) % 200 == 0:
            print(json.dumps({"preprocessed": index + 1, "total": len(samples)}), flush=True)
    images, labels = np.stack(images), np.array(labels, np.int64)
    np.savez_compressed(cache, images=images, labels=labels)
    return images, labels, samples


def evaluate(model, loader, device):
    model.eval()
    output, targets = [], []
    with torch.inference_mode():
        for images, labels in loader:
            output.append(model(images.to(device)).cpu().numpy())
            targets.append(labels.numpy())
    return np.concatenate(targets), np.concatenate(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--architecture", choices=["mobilenet_v3_small", "resnet18"], default="mobilenet_v3_small")
    parser.add_argument("--side", type=int, choices=[224, 384], default=224)
    args = parser.parse_args()
    CONFIG.update(architecture=args.architecture, side=args.side)
    torch.set_num_threads(4)
    random.seed(CONFIG["seed"])
    np.random.seed(CONFIG["seed"])
    torch.manual_seed(CONFIG["seed"])
    cv2.setNumThreads(2)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    manifest = json.loads((ROOT / "datasets/pd_defect/pole-development-manifest.json").read_text())
    assert not manifest["includes_test"]
    images, labels, samples = load_data(manifest)
    train_hashes = {x["sha256"] for x in samples if x["split"] == "train"}
    train = np.array([i for i, sample in enumerate(samples) if sample["split"] == "train"])
    validation = np.array([i for i, sample in enumerate(samples) if sample["split"] == "val" and sample["sha256"] not in train_hashes])
    training_loader = DataLoader(Images(images[train], labels[train], True), batch_size=CONFIG["batch_size"], shuffle=True, num_workers=0)
    validation_loader = DataLoader(Images(images[validation], labels[validation]), batch_size=CONFIG["batch_size"], num_workers=0)
    if args.architecture == "mobilenet_v3_small":
        model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
        model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, 3)
    else:
        backbone = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        model = nn.Sequential(OrderedDict(features=nn.Sequential(*list(backbone.children())[:-1]),
                                        classifier=nn.Sequential(nn.Flatten(), nn.Dropout(.2), nn.Linear(512, 3))))
    for parameter in model.features.parameters():
        parameter.requires_grad = False
    model.to(device)
    counts = np.bincount(labels[train], minlength=3)
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(len(train) / (3 * counts), dtype=torch.float32, device=device))
    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=CONFIG["head_lr"], weight_decay=CONFIG["weight_decay"])
    print(json.dumps({"device": device, "train": len(train), "validation": len(validation), "train_counts": counts.tolist(), "config": CONFIG}), flush=True)
    best, best_state, history = -1, None, []
    destination = ROOT / "data" / "experiments" / f"{args.architecture}-{args.side}"
    destination.mkdir(parents=True, exist_ok=True)
    for epoch in range(CONFIG["epochs"]):
        start = time.perf_counter()
        if epoch == CONFIG["frozen_epochs"]:
            for parameter in model.features.parameters():
                parameter.requires_grad = True
            optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG["fine_tune_lr"], weight_decay=CONFIG["weight_decay"])
        model.train()
        if epoch < CONFIG["frozen_epochs"]:
            model.features.eval()
        total_loss = 0
        for inputs, target in training_loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(inputs.to(device))
            loss = criterion(logits, target.to(device))
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach().cpu()) * len(target)
        actual, logits = evaluate(model, validation_loader, device)
        result = {"epoch": epoch + 1, "seconds": round(time.perf_counter() - start, 1),
                  "train_loss": round(total_loss / len(train), 4), **metrics(actual, logits)}
        history.append(result)
        print(json.dumps(result), flush=True)
        if result["macro_f1"] > best:
            best = result["macro_f1"]
            best_state = copy.deepcopy({name: value.cpu() for name, value in model.state_dict().items()})
            torch.save(best_state, destination / "pole-triage-state.pt")
    model.cpu().load_state_dict(best_state)
    model.eval()
    model_dir = destination
    onnx_path = model_dir / "pole-triage.onnx"
    example = torch.from_numpy(Images(images[validation[:1]], labels[validation[:1]])[0][0].numpy()[None])
    torch.onnx.export(model, example, onnx_path, input_names=["image"], output_names=["logits"], opset_version=17, dynamo=False)
    net = cv2.dnn.readNetFromONNX(str(onnx_path))
    net.setInput(example.numpy())
    cv_logits = net.forward()
    with torch.inference_mode():
        torch_logits = model(example).numpy()
    error = float(np.max(np.abs(cv_logits - torch_logits)))
    if error > .002:
        raise RuntimeError(f"OpenCV and PyTorch logits disagree: {error}")
    actual, logits = evaluate(model, validation_loader, "cpu")
    best_metrics = metrics(actual, logits)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "configuration": CONFIG, "device": device,
              "torch": torch.__version__, "opencv": cv2.__version__, "dataset_revision": manifest["revision"],
              "train_count": len(train), "validation_count": len(validation), "validation_duplicates_excluded": int(sum(x["split"] == "val" for x in samples) - len(validation)),
              "test_evaluated": False, "model_sha256": hashlib.sha256(onnx_path.read_bytes()).hexdigest(),
              "onnx_max_logit_error": error, "validation": best_metrics, "history": history,
              "predictions": [{"path": samples[index]["path"], "actual": CLASSES[int(actual[i])], "predicted": CLASSES[int(logits[i].argmax())], "logits": logits[i].tolist()} for i, index in enumerate(validation)],
              "limits": ["Validation selected the checkpoint; these are not held-out test scores.", "Publisher image labels are not instrument measurements or certified asset severity.", "Site-level overlap and geographic transfer remain unverified."]}
    (ROOT / f"reports/pole-model-{args.architecture}-{args.side}.json").write_text(json.dumps(report, indent=2) + "\n")
    (model_dir / "pole-triage.json").write_text(json.dumps({key: report[key] for key in ["configuration", "dataset_revision", "model_sha256", "validation", "test_evaluated", "limits"]}, indent=2) + "\n")
    print(json.dumps({"result": "exported", "validation": best_metrics, "onnx_max_logit_error": error}), flush=True)


if __name__ == "__main__":
    main()
