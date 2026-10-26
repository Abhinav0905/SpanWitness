# Final demo support files

The final video uses one continuous Python-generated narration, not stitched speech clips. Install `requirements.txt` in a separate media environment, then run `python demo-video/generate_final_narration.py` from the repository root. It writes the MP3 and word timings under `remotion-demo/public/final/`. Online speech synthesis requires a network connection. No API key is included.

With the application's pinned dependencies installed, run `python demo-video/build_opencv_evidence.py` from the root to capture actual Canny, HoughLinesP and fitLine outputs. It wraps the same analyze() function without changing its results and writes diagnostic images and a trace under `remotion-demo/public/opencv-evidence/`.

The narrated script, final captions, processing figure and recorded trace are in `docs/media/`. These two selected real photos are functional examples, not a field accuracy benchmark. The final video render project is a separate media workspace; these support scripts reproduce the speech and pipeline diagnostics.
