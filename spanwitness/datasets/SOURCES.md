# Public data intake

Checked October 25, 2026. Public documents can inform the inspection workflow; dataset images need a recorded source and reuse license.

## PD-Defect: selected for the first field sample

- Publisher repository: [EPDCL/pd-defect](https://huggingface.co/datasets/EPDCL/pd-defect).
- DOI: [10.6084/m9.figshare.34329402](https://doi.org/10.6084/m9.figshare.34329402).
- Publisher-declared license: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Authors: Sampath Balaji Masabathula, Srija Vanapalli, Gangadhar Kanchi, Sreenivasa Rao V.A.N, Vijaya Lalitha V and Sasank Chilamkurthy.
- Revision is pinned in `scripts/fetch_public_data.py` and the generated [manifest](pd_defect/MANIFEST.json).

The first selection uses only the publisher's validation splits: eight Leaned, eight Straight and eight Rejected pole images, plus six Risky and six Safe vegetation/conductor images. Selection follows a deterministic hash ordering of source paths, not model scores. The original labels and vegetation polygons are retained separately from image analysis.

The script downloads raw images into the ignored `data/public_datasets/pd_defect/` directory. The manifest contains source URLs, hashes, sizes, split names, publisher labels and attribution. The source archive includes the manifest and a reproducer. It also includes the two credited demonstration photographs described below.

Publisher labels are not our model's predictions. The pole labels do not provide instrument-measured physical lean. Vegetation labels and masks do not provide metric clearance or wildfire probability. A small, class-balanced sample does not estimate the prevalence of conditions in a utility network. Keep the publisher's test split untouched until the method and evaluation procedure are frozen.

Before public display, inspect faces, number plates and other identifiers. Raw data intake is not a privacy clearance. Keep credit and a note of any resize, annotation or other image changes with displayed derivatives.

Reproduce from the workspace root:

```sh
.venv/bin/python -m spanwitness.scripts.fetch_public_data
```

## PG&E overhead-inspection job aid: reference document

[Official public PDF](https://www.pge.com/assets/pge/docs/outages-and-safety/outage-preparedness-and-support/td-2305m-ja02-overhead-inspection-job-aid.pdf), TD-2305M-JA02, revision 9, dated March 23, 2022. The source includes leaning poles, conductor conditions and vegetation examples. It carries a PG&E copyright and an all-rights-reserved notice.

A local reference copy is in `data/public_references/`; it is excluded from the app and source archive. Keep the link for source-backed explanations rather than treating the guide as an openly licensed image dataset. This historical document is not asserted to be the current operating standard. Its physical inspection guidance is not a calibration for a single photograph or our prototype's review thresholds.

## Insulator dataset: candidate for a later module

[Porcelain Disk type insulators](https://data.mendeley.com/datasets/5pwrd7gmw2/1), Shafi Jiskani (2026), DOI [10.17632/5pwrd7gmw2.1](https://doi.org/10.17632/5pwrd7gmw2.1). The publisher describes 255 aerial images with condition annotations and a CC BY 4.0 license.

Not downloaded or used by the current model. Insulator-condition detection requires its own model, evaluation and failure cases; it is not part of the conductor-edge screen.

## Two public demonstration photographs

Photographs 713 and 1005 from the pinned validation revision are bundled as `static/samples/field-house.jpg` and `field-warehouse.jpg`. They were selected after visual inspection to explain one supported alignment screen and one insufficient-edge case. This is a selected smoke check, not a blinded accuracy evaluation. Neither image represents a school, and they are different assets, not a before/after pair.

The original JPEG bytes are preserved. Neither file contains EXIF. A visual review found no identifiable faces or readable vehicle plates. Source hashes, complete author credit, CC BY 4.0 links and modification notes are in `static/samples/ATTRIBUTION.json`. The app's gold and blue lines are example operator annotations; they are not publisher labels or automatic pole identification. Annotated outputs are derivatives of those photographs.
