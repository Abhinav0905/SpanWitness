# Data and image rights

No workplace source code, screenshots or asset imagery is part of this application. The workplace POC informed the problem only.

## Original fixtures

`examples.py` draws eight controlled cases with OpenCV. The labels are expectations used by tests; labels are not inputs to perception. Some examples include operator-like path and axis annotations. The UI presents them as synthetic, including the second-view pairs.

These drawings do not simulate electrical contact, fire propagation or full 3D parallax. They exercise defined image changes and the resulting workflow.

## Licensed field photographs

| File | Creator and title | Source | License |
| --- | --- | --- | --- |
| `field-crossing.jpg` | Paul Harrop, "Crossed Wires II" | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Crossed_Wires_II_-_geograph.org.uk_-_566910.jpg) | [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/) |
| `field-span.jpg` | Andy Beecroft, "Power from Afar" | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Power_from_Afar_-_geograph.org.uk_-_657646.jpg) | [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/) |

The bundled files are the downloaded 640-pixel photographs. OpenCV may resize, recompress and annotate them during analysis. Distribute derived image versions under the same image license and retain the creator, source link and a note of changes. The image license does not determine the license for unrelated application code.

Raw file hashes, original download URLs and license URLs are recorded in [ATTRIBUTION.json](static/samples/ATTRIBUTION.json). No expert defect or safety label is assigned to either photograph.

## PD-Defect demonstration photographs

Two additional real photographs are distributed under the publisher-declared [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) license: `field-house.jpg` (713) and `field-warehouse.jpg` (1005). Authors: Sampath Balaji Masabathula, Srija Vanapalli, Gangadhar Kanchi, Sreenivasa Rao V.A.N, Vijaya Lalitha V and Sasank Chilamkurthy. Source: [EPDCL/pd-defect](https://huggingface.co/datasets/EPDCL/pd-defect), pinned revision `b9c64b2f9615ef5ade71fceade7d9d31b0dc9416`.

The JPEG bytes are unchanged and contain no EXIF. A visual review found no identifiable faces or readable vehicle plates. The app adds example operator marks and generates annotated derivatives. Retain author credit, license and a note of those changes. Full URLs and hashes are in the attribution file. The photographs are different assets, not a before/after pair. Selected demonstration results are recorded in [FIELD_PHOTOS.md](reports/FIELD_PHOTOS.md); no field accuracy is inferred.

## Future capture

Use independently created footage or images with clear reuse permission. Keep an inventory of source, creator, rights and visible-condition annotations. Do not import employer, customer or private utility data into a public submission without permission.

## Public field dataset intake

The [public-source catalog](datasets/SOURCES.md) records PD-Defect, the PG&E reference guide and a candidate insulator dataset. A revision-pinned downloader selects a small labeled PD-Defect validation sample. Raw downloaded photographs stay in the ignored data directory. Only the two separately reviewed and credited demonstration images above are bundled publicly.

The existing synthetic evaluation results are unchanged by data intake. A separate field evaluation must run before reporting scores on the new images.
