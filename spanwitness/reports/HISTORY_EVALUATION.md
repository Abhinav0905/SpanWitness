# History comparison development checks

Checked with OpenCV 5.0.0. 108 / 108 expected decision branches passed.

Three background seeds, three image scales and three JPEG quality settings were applied to four controlled pairs: a drawn 5-degree change, a camera rotation without pole movement, changed perspective and a blurred follow-up.

The accepted apparent-angle measurements had median absolute error 0.05 degrees and maximum error 0.59 degrees against the drawing geometry. Controls produced 0 change alerts. These are image-space fixture results, not physical pole measurements.

The first four checks exposed biased axis fits and excessive abstention on camera rotation. Directional-edge selection with Hough support and mutual background matching were introduced after those checks. Original results remain in [history-baseline.json](history-baseline.json).

All branches, including failed checks, are retained in [history-evaluation.json](history-evaluation.json). These development checks share a procedural scene design. They establish neither field precision/recall nor accuracy on arbitrary camera poses. Asset IDs, dates, selected axes and repeatable capture are operator supplied. Comparison is conditional on that setup. No fall date, structural strength or fire forecast is inferred.
