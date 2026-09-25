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


def still_clip(png: Path, mp4: Path, secs: float):
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-t", f"{secs}", "-i", str(png),
         "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0b1020,format=yuv420p",
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
    title_card(tc, "MIRAGE", ["the backtest lie detector", "GIBC V2 · Track 02"])
    title_card(ec, "MIRAGE", ["github.com/sharonbasovich/mirage",
                              "research prototype · not financial advice"])
    still_clip(tc, SEGS / "01_title.mp4", 15)
    still_clip(FIGS / "e1_sharpe_histogram.png", SEGS / "02_e1fig.mp4", 25)
    still_clip(FIGS / "e2_roc.png", SEGS / "08_e2fig.mp4", 22)
    still_clip(FIGS / "e3_scorecard.png", SEGS / "09_e3fig.mp4", 20)
    still_clip(ec, SEGS / "10_end.mp4", 12)

    # normalize recorded webm -> mp4 uniform
    for w in SEGS.glob("0*_*.webm"):
        out = w.with_suffix(".mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(w),
             "-vf", f"scale={W}:{H},format=yuv420p",
             "-r", "30", "-c:v", "libx264", "-preset", "fast", str(out)],
            check=True, capture_output=True)

    order = ["01_title.mp4", "02_e1fig.mp4", "03_lab.mp4", "04_run.mp4",
             "05_verdict.mp4", "06_ledger.mp4", "07_upload.mp4", "075_about.mp4",
             "08_e2fig.mp4", "09_e3fig.mp4", "10_end.mp4"]
    subs = {
        "01_title.mp4": "Anyone can build a trading strategy with a three-hundred-percent backtest. Almost none survive live. The reason isn't bad code — it's selection bias.",
        "02_e1fig.mp4": "We ran one thousand random, zero-skill strategies on real S&P data. The best backtest looks great — a Sharpe of 0.61. It's pure luck, and the math knows it.",
        "03_lab.mp4": "Mirage backtests your strategy grid on real market data with realistic costs — and remembers every single trial.",
        "04_run.mp4": "Every trial lands in a tamper-evident Trial Ledger: pre-registration for backtests. You can't quietly delete the losers. Then the overfitting battery runs: Deflated Sharpe Ratio, CSCV, Reality Check.",
        "05_verdict.mp4": "The verdict card: PBO — the probability the in-sample winner underperforms out of sample — is sixty-five percent. Flagged unclear, leaning overfit. Don't trust it.",
        "06_ledger.mp4": "Every trial is hash-chained — timestamp, config hash, data hash. Export a pre-registration certificate any third party can verify.",
        "07_upload.mp4": "Already used another backtester? Upload your returns and a trial count — Mirage audits the field, not just its own runs.",
        "075_about.mp4": "Every method is from the published literature — Deflated Sharpe Ratio, CSCV, White's Reality Check, purged cross-validation — with formulas and citations on the methods page.",
        "08_e2fig.mp4": "And Mirage validates itself — planted-skill experiments measure the detector's own ROC AUC at point nine, and the verdict label's own accuracy on ground truth.",
        "09_e3fig.mp4": "DSR alone misses forty-five percent of zero-skill zoos — the combined battery misses none. The verdict is a battery, not a number.",
        "10_end.mp4": "Mirage — free, open source, MIT licensed. Stop trusting your own backtests.",
    }

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
    for i, start, end, text in cues:
        wav = SEGS / f"narr_{i}.wav"
        dur = tts(text, wav)
        if dur <= 0:
            continue
        slot = end - start
        tempo = dur / slot if dur > slot else 1.0
        tempo = min(tempo, 1.6)
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
