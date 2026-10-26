# Final demo

[Watch the 1080p video](https://youtu.be/Qj62M_E8ptI). Duration: 3 minutes 16 seconds, 1920 x 1080, 30 fps.

The opening holds the actual application UI while the narration explains the inspection problem. The video then shows actual Canny edges, HoughLinesP candidates and Huber line fits from the same OpenCV 5 analyze() function used by the app. AWS architecture comes next, followed by a supported real-photo inspection, human review, an insufficient-edge refusal, dated history, runtime evidence and limitations. No AI concept-art scene is used in this edit.

One continuous narration was generated in Python using edge-tts 7.3.1, voice en-US-AriaNeural, rate -5%. No Suno clips are used in this version and no audio purchase was made. The complete independent transcript was checked against the script, including the 108 history checks, no-external-notification line and creator credit. Sampled audio in the encoded MP4 correlates above 0.996 with the verified source narration.

- [Full narration script](media/SpanWitness-final-narration.txt)
- [Timed English captions](media/SpanWitness-final-demo.srt)
- [Actual OpenCV processing figure](media/SpanWitness-OpenCV-processing.png)
- [OpenCV call trace and source attribution](media/opencv-processing-trace.json)
- [Speech and diagnostic reproduction scripts](../demo-video/README.md)

The video displays the private AWS origin, server-reported OpenCV/Lambda runtime and AWS CloudShell verification of matching S3/DynamoDB records. The preview credential is supplied only in the judges-and-organizers testing field, never in this repository or the video.

One real PD-Defect photograph produces a 19.32-degree image-relative edge difference, displayed as 19.3. Another real photograph is an insufficient-edge case. They are different assets, not before/after images. The dated history view is a separate original synthetic example with illustrative dates.

Photo credits and license: [DATA.md](../spanwitness/DATA.md), [pinned image attribution](../spanwitness/static/samples/ATTRIBUTION.json). The real-photo cover crops the original photograph for layout; app screenshots and diagnostic views add operator marks, crops and fitted-line overlays. The photos are CC BY 4.0.

Checks: [field examples](../spanwitness/reports/FIELD_PHOTOS.md), [actual cloud records](../spanwitness/reports/aws-real-photo-receipt.json), [cloud regression receipt](../spanwitness/reports/aws-field-live-receipt.json). These selected functional checks do not establish field accuracy.
