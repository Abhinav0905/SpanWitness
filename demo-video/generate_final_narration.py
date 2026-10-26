"""Generate the revised narration with one consistent speech-synthesis voice."""
from pathlib import Path
import asyncio
import hashlib
import json

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "demo-video/spanwitness-single-take-script-v2.txt"
OUTPUT = ROOT / "remotion-demo/public/final"


async def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    text = SCRIPT.read_text().strip()
    # Spoken pronunciation only. Captions retain the correct algorithm name.
    speech = text.replace("Hough transform", "Huff transform")
    voice = "en-US-AriaNeural"
    synth = edge_tts.Communicate(speech, voice, rate="-5%", boundary="WordBoundary")
    boundaries = []
    with (OUTPUT / "narration.mp3").open("wb") as audio:
        async for item in synth.stream():
            if item["type"] == "audio":
                audio.write(item["data"])
            elif item["type"] == "WordBoundary":
                boundaries.append({"start": item["offset"] / 10_000_000,
                                   "duration": item["duration"] / 10_000_000,
                                   "text": item["text"]})
    assert boundaries and (OUTPUT / "narration.mp3").stat().st_size > 100_000
    (OUTPUT / "boundaries.json").write_text(json.dumps(boundaries, indent=2) + "\n")
    receipt = {"provider": "Microsoft Edge online speech synthesis via edge-tts",
               "edge_tts_version": "7.3.1", "voice": voice, "rate": "-5%",
               "script": str(SCRIPT.relative_to(ROOT)), "script_words": len(text.split()),
               "script_sha256": hashlib.sha256(text.encode()).hexdigest(),
               "audio_sha256": hashlib.sha256((OUTPUT / "narration.mp3").read_bytes()).hexdigest(),
               "pronunciation_change": "Hough spoken as Huff; displayed spelling remains Hough.",
               "word_boundaries": len(boundaries), "last_word": boundaries[-1],
               "paid_purchase": False, "status": "generated_not_yet_verified"}
    (ROOT / "demo-video/final-narration-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
