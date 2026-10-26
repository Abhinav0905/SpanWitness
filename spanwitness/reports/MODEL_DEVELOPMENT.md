# Pole-appearance experiments

Neither model is loaded by the application. The current preview uses OpenCV image measurements and operator-selected geometry.

## Data and method

PD-Defect revision `b9c64b2f9615ef5ade71fceade7d9d31b0dc9416` supplied 1706 training and 341 validation images. Class counts were 464/280/962 in training and 93/57/191 in validation for Leaned/Rejected/Straight. No exact-byte duplicate was found across these two splits. Site overlap and geographic transfer remain unverified. The publisher's 227-image test split was not downloaded or evaluated.

Both runs used seed 42, eight epochs, two initial frozen-backbone epochs, weighted cross entropy and whole-image letterboxing. Validation macro-F1 selected the checkpoint. The second experiment had a declared minimum validation macro-F1 of 0.70 before consideration for UI integration. A frozen held-out test would still be required before a deployment claim.

| Validation result | MobileNetV3-Small, 224 px | ResNet18, 384 px |
| --- | --- | --- |
| Accuracy | 0.6804 | 0.7478 |
| Macro-F1 | 0.6143 | 0.6925 |
| Leaned recall | 0.5269 | 0.4409 |
| Rejected recall | 0.4211 | 0.6316 |
| Straight recall | 0.8325 | 0.9319 |
| Coverage at max softmax >= 0.65 | 0.6716 | 0.9267 |
| Maximum OpenCV/PyTorch logit difference | 4.30e-6 | 2.39e-6 |

ResNet18 missed 52 of 93 Leaned examples. Its higher accuracy does not justify a condition-monitoring claim. A Straight image label cannot certify safety, and a softmax score is not a calibrated probability of asset condition.

The ONNX exports run numerically through OpenCV 5, but numerical agreement does not establish predictive quality. Both experiments remain outside the application. We did not lower the integration threshold after seeing the second result.

## Reproduction and records

- [Fixed experiment plan](../datasets/POLE_MODEL_PLAN.md)
- [Data sources and pinned intake](../datasets/SOURCES.md)
- [MobileNet run, confusion matrix and per-image predictions](pole-model-development.json)
- [ResNet run, confusion matrix and per-image predictions](pole-model-resnet18-384.json)

Use `scripts/prepare_pole_training_data.py` and `scripts/train_pole_model.py` with the separate ML requirements. Weights and raw images remain in the ignored local `data/` directory. They are not Lambda dependencies or bundled public photographs. Publisher labels describe image appearance, not instrument-measured lean, strength or urgency.
