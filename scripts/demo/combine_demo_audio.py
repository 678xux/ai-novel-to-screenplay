from __future__ import annotations

import argparse
import json
from pathlib import Path
import wave


def seconds_to_srt_time(value: float) -> str:
    total_ms = int(round(value * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def read_wav(path: Path) -> tuple[wave._wave_params, bytes, float]:
    with wave.open(str(path), "rb") as source:
        params = source.getparams()
        frames = source.readframes(source.getnframes())
        duration = source.getnframes() / source.getframerate()
    return params, frames, duration


def silence(params: wave._wave_params, duration_seconds: float) -> bytes:
    frame_count = int(params.framerate * duration_seconds)
    return b"\x00" * frame_count * params.nchannels * params.sampwidth


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--audio-dir", required=True)
    parser.add_argument("--out-audio", required=True)
    parser.add_argument("--out-srt", required=True)
    parser.add_argument("--out-timeline", required=True)
    args = parser.parse_args()

    script_path = Path(args.script)
    audio_dir = Path(args.audio_dir)
    out_audio = Path(args.out_audio)
    out_srt = Path(args.out_srt)
    out_timeline = Path(args.out_timeline)
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    out_timeline.parent.mkdir(parents=True, exist_ok=True)

    segments = json.loads(script_path.read_text(encoding="utf-8"))
    wav_items = []
    base_params = None
    for index, segment in enumerate(segments, start=1):
        params, frames, duration = read_wav(audio_dir / f"segment_{index:02d}.wav")
        if base_params is None:
            base_params = params
        elif (
            params.nchannels,
            params.sampwidth,
            params.framerate,
            params.comptype,
        ) != (
            base_params.nchannels,
            base_params.sampwidth,
            base_params.framerate,
            base_params.comptype,
        ):
            raise ValueError("All generated WAV files must use the same audio parameters.")
        wav_items.append((segment, frames, duration))

    if base_params is None:
        raise ValueError("No audio segments were generated.")

    gap_seconds = 0.45
    current = 0.0
    timeline = []
    srt_blocks = []
    with wave.open(str(out_audio), "wb") as target:
        target.setparams(base_params)
        for index, (segment, frames, duration) in enumerate(wav_items, start=1):
            start = current
            end = start + duration
            target.writeframes(frames)
            timeline.append(
                {
                    "index": index,
                    "image": segment["image"],
                    "text": segment["text"],
                    "start": round(start, 3),
                    "end": round(end, 3),
                }
            )
            srt_blocks.append(
                f"{index}\n{seconds_to_srt_time(start)} --> {seconds_to_srt_time(end)}\n{segment['text']}\n"
            )
            current = end
            if index < len(wav_items):
                target.writeframes(silence(base_params, gap_seconds))
                current += gap_seconds

    out_srt.write_text("\n".join(srt_blocks), encoding="utf-8")
    out_timeline.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created {out_audio} and {out_srt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
