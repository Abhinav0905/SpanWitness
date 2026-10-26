# Pole-appearance pilot model: fixed first experiment

This experiment addresses a gap in the initial app: automatic pole-appearance triage requires a learned model or an operator's marked axes. The current geometric screen alone does not recognize a leaning pole in an arbitrary photograph.

## Data roles

Use PD-Defect's original pole-classification train and validation splits. Initialize a MobileNetV3-Small backbone with Torchvision's ImageNet weights. Keep the publisher's test split untouched until the model, thresholds and evaluation code are frozen.

Keep source images and publisher labels outside the inference API. Detect exact byte duplicates between development splits, exclude training duplicates from validation scoring and report how many were excluded. Repeated views of the same site may still create correlation; byte deduplication does not establish a site-disjoint benchmark.

## First training configuration

- Class order: Leaned, Rejected, Straight.
- Seed 42; eight epochs, first two with the feature backbone frozen.
- Whole-image letterboxing to 224 pixels. No crop or rotation augmentation, since those can change the pole-visibility or alignment label.
- Horizontal flips and modest brightness/contrast variation on the training split only.
- AdamW; inverse-frequency class-weighted cross entropy; best checkpoint chosen by validation macro-F1.
- A maximum softmax score below 0.65 requests more evidence. Scores are uncalibrated model outputs, not certified condition probabilities.

Export the selected model to ONNX, compare OpenCV DNN logits with the training runtime and save the version, model hash, configuration and per-image predictions. The deployed inference path must run through OpenCV 5, with no PyTorch dependency in Lambda.

## Acceptance boundary

Report the actual confusion matrix, per-class recall, macro-F1, coverage under the abstention rule and failure examples. Do not copy the dataset author's benchmark scores into our results.

The model predicts an image appearance class. It does not measure true physical lean, pole strength or defect urgency. Its Straight output cannot certify safety or overrule a separate unresolved finding. A usable prototype may request another view; a weak model will remain an experiment rather than an advertised feature.

## Second declared experiment

The first MobileNetV3-Small run reached validation macro-F1 0.6143. Leaned recall was 0.5269. It remains an experiment and is not loaded by the application.

Try a ResNet18 backbone with 384-pixel whole-image letterboxing to preserve more pole detail. Keep the same seed, eight-epoch schedule, data roles and validation selection rule. Do not open the test split during this comparison. Record this run separately and require validation macro-F1 of at least 0.70 before considering a pilot UI integration; deployment claims still require a frozen held-out test evaluation.
