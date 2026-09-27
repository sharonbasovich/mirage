"""Assemble the Mirage demo MP4: title cards + figure stills + recorded scenes,
with burned-in English subtitles (also written out as submission/mirage.srt)
and an offline Piper TTS narration track muxed in as AAC.

Run after scripts/record_demo.py. Requires ffmpeg + ffprobe and a downloaded
piper voice (en_US-lessac-medium.onnx[.json] at repo root or SEGS dir).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEGS = ROOT / "submission" / "video_segments"
FIGS = ROOT / "reports" / "figures"
OUT = ROOT / "submission" / "mirage_demo.mp4"
SRT = ROOT / "submission" / "mirage.srt"
W, H = 1920, 1080
PY = sys.executable


def piper_model() -> Path | None:
    for c in (ROOT / "en_US-lessac-medium.onnx",
              SEGS / "en_US-lessac-medium.onnx"):
        if c.exists() and c.with_suffix(".onnx.json").exists():
            return c
    return None


def tts(text: str, wav: Path) -> float:
    """Synthesize text via piper -> wav path; returns duration in seconds."""
    model = piper_model()
    if model is None:
        return 0.0
    subprocess.run(
        [PY, "-m", "piper", "-m", str(model), "-f", str(wav),
         "--sentence-silence", "0.25"],
        input=text.encode(), check=True, capture_output=True)
    return ffprobe_dur(wav)


def ffprobe_dur(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(p)],
        capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def title_card(path: Path, big: str, small: list[str]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor="#0b1020")
    fig.text(0.5, 0.58, big, ha="center", va="center", color="#38bdf8",
             fontsize=64, weight="bold", family="monospace")
    for i, s in enumerate(small):
        fig.text(0.5, 0.42 - i * 0.07, s, ha="center", va="center",
                 color="#94a3b8", fontsize=22, family="monospace")
    fig.savefig(path, facecolor="#0b1020")
    plt.close(fig)


FIG_H = 800  # keep figures above the burned-in subtitle band


def still_clip(png: Path, mp4: Path, secs: float):
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-t", f"{secs}", "-i", str(png),
         "-vf", f"scale={W}:{FIG_H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:({FIG_H}-ih)/2+20:color=0x0b1020,format=yuv420p",
         "-r", "30", "-c:v", "libx264", "-preset", "fast", str(mp4)],
        check=True, capture_output=True)


def srt_ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def main():
    SEGS.mkdir(parents=True, exist_ok=True)
    tc = SEGS / "title_card.png"
    ec = SEGS / "end_card.png"
    title_card(tc, "MIRAGE", ["the backtest lie detector", "GIBC V2 · Track 02",
                              "data: World Bank Pink Sheet (CC BY 4.0) + synthetic series"])
    title_card(ec, "MIRAGE", ["github.com/sharonbasovich/mirage",
                              "data: World Bank Commodity Price Data (The Pink Sheet), CC BY 4.0",
                              "historical simulation only · research prototype · not financial advice"])
    for old in ("02_e1fig.mp4", "09_e3fig.mp4"):
        (SEGS / old).unlink(missing_ok=True)
    still_clip(tc, SEGS / "01_title.mp4", 12)
    still_clip(FIGS / "e2_power.png", SEGS / "08_e2power.mp4", 16)
    still_clip(FIGS / "e2_roc.png", SEGS / "085_e2roc.mp4", 16)
    still_clip(FIGS / "e4_worldbank_scorecard.png", SEGS / "09_e4fig.mp4", 14)
    still_clip(ec, SEGS / "10_end.mp4", 10)

    # normalize recorded webm -> mp4 uniform
    for w in SEGS.glob("0*_*.webm"):
        out = w.with_suffix(".mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(w),
             "-vf", f"scale={W}:{H},format=yuv420p",
             "-r", "30", "-c:v", "libx264", "-preset", "fast", str(out)],
            check=True, capture_output=True)

    order = ["01_title.mp4", "03_lab.mp4", "04_run.mp4", "05_verdict.mp4",
             "06_ledger.mp4", "07_upload.mp4", "075_about.mp4",
             "08_e2power.mp4", "085_e2roc.mp4", "09_e4fig.mp4", "10_end.mp4"]
    subs = {
        "01_title.mp4": "Try fifty parameter combinations, keep the best one, and part of that winning backtest is luck. That is selection bias, and Mirage is built to measure it.",
        "03_lab.mp4": "Mirage backtests a whole strategy grid on historical data with transaction costs. The bundled data is the World Bank Pink Sheet: monthly commodity reference prices, licensed CC BY 4.0. These are hypothetical price-series backtests, not realizable trading profits.",
        "04_run.mp4": "One click runs twelve moving-average crossover trials on gold. Every trial is appended to a hash-chained Trial Ledger, and the diagnostics use that full trial count: Deflated Sharpe Ratio, CSCV, and White's Reality Check.",
        "05_verdict.mp4": "The best trial has a Sharpe of 0.71, and a deflated Sharpe confidence of 1.00. That is an exceedance estimate over the best-of-twelve luck threshold, not the probability of genuine skill. Overfitting risk is low: PBO is 23 percent. But the Reality Check p-value against holding gold is 0.59, so there is insufficient evidence of outperformance. The verdict is capped at Unclear, with a score of 81.",
        "06_ledger.mp4": "Each ledger entry hashes its timestamp, config, data hash, and the previous entry. That detects edits or deletions within an intact ledger. The chain is not signed or externally anchored, so the exported certificate is unsigned.",
        "07_upload.mp4": "Already using another backtester? Upload a returns CSV, here a set of synthetic strategies, with a declared trial count, and Mirage runs the same audit.",
        "075_about.mp4": "Every method comes from the academic literature, with formulas and citations on the methods page.",
        "08_e2power.mp4": "Does the detector work? In experiment E2 we plant known skill in one of fifty synthetic strategies. When the skilled strategy wins in-sample, the verdict says Survives 82.5 percent of the time at a true Sharpe of 1.5, and 97.5 percent at 2.0.",
        "085_e2roc.mp4": "On pure-noise zoos, the label says Survives only 5 percent of the time, while a DSR confidence above 0.5 alone would flag 57.5 percent. Across 320 synthetic zoos the label is right 82 percent of the time. ROC AUC is 0.91 for DSR and 0.90 for PBO.",
        "09_e4fig.mp4": "Experiment E4 runs four hypothetical zoos on the bundled World Bank prices: gold crossover, Brent momentum, commodity momentum, and gold RSI. None shows sufficient evidence of beating its benchmark after data snooping, so all four are Unclear, with scores from 52 to 87. Futures roll, storage, and financing are not modeled.",
        "10_end.mp4": "Mirage is free, open source, and MIT licensed. Data: World Bank Pink Sheet, CC BY 4.0. It is a historical-simulation research prototype, not financial advice.",
    }

    # synthesize narration first; extend any segment that is shorter than its line
    narr: dict[str, float] = {}
    for i, name in enumerate(order, 1):
        narr[name] = tts(subs[name], SEGS / f"narr_{i}.wav")
        need = narr[name] + 0.8
        have = ffprobe_dur(SEGS / name)
        if need > have:
            tmp = SEGS / f"pad_{name}"
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(SEGS / name),
                 "-vf", f"tpad=stop_mode=clone:stop_duration={need - have:.2f}",
                 "-r", "30", "-c:v", "libx264", "-preset", "fast", str(tmp)],
                check=True, capture_output=True)
            tmp.replace(SEGS / name)

    durs = {}
    t = 0.0
    cues = []
    for i, name in enumerate(order, 1):
        d = ffprobe_dur(SEGS / name)
        durs[name] = d
        cues.append((i, t, t + d, subs[name]))
        t += d
    (SEGS / "durations.json").write_text(json.dumps(durs, indent=1))
    print(json.dumps(durs, indent=1), "total", t)

    srt = "\n\n".join(
        f"{i}\n{srt_ts(a)} --> {srt_ts(b)}\n{text}" for i, a, b, text in cues)
    SRT.write_text(srt + "\n")

    # narration: synthesize one wav per cue, time-fit into its segment slot
    narr_inputs: list[str] = []
    narr_filter: list[str] = []
    mix_names: list[str] = []
    for i, start, _end, _text in cues:
        wav = SEGS / f"narr_{i}.wav"
        if narr[order[i - 1]] <= 0:
            continue
        tempo = 1.0
        narr_inputs += ["-i", str(wav)]
        ms = int(start * 1000)
        narr_filter.append(
            f"[{len(narr_inputs) // 2}:a]aformat=sample_rates=44100:"
            f"channel_layouts=stereo,atempo={tempo:.3f},adelay={ms}|{ms}[a{i}]")
        mix_names.append(f"[a{i}]")

    lst = SEGS / "concat.txt"
    lst.write_text("".join(f"file '{(SEGS / n).resolve()}'\n" for n in order))
    if narr_filter:
        fc = ";".join(narr_filter) + ";" + "".join(mix_names) + (
            f"amix=inputs={len(mix_names)}:dropout_transition=0:normalize=0"
            f"[mix];[mix]alimiter=limit=0.9:level=false[narr]")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             *narr_inputs,
             "-filter_complex", fc,
             "-map", "0:v", "-map", "[narr]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-r", "30",
             "-vf", f"subtitles={SRT}:force_style="
                    "'FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
                    "Outline=2,Alignment=2,MarginV=40,FontName=DejaVu Sans'",
             "-c:a", "aac", "-b:a", "160k",
             str(OUT)],
            check=True)
    else:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-r", "30",
             "-vf", f"subtitles={SRT}:force_style="
                    "'FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
                    "Outline=2,Alignment=2,MarginV=40,FontName=DejaVu Sans'",
             str(OUT)],
            check=True)
    print("wrote", OUT, ffprobe_dur(OUT), "s")


if __name__ == "__main__":
    main()
