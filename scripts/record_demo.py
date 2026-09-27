"""Record the Mirage demo video + UI screenshots with Playwright.

Scenes are recorded as separate webm clips (one browser context each) so that
subtitle cue boundaries land exactly on measured segment durations. Assembly
(title cards, figure stills, concat, subtitle burn) is done with ffmpeg by
scripts/assemble_video.py.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SEGS = ROOT / "submission" / "video_segments"
SHOTS = ROOT / "submission" / "screenshots"
BASE = "http://localhost:8000"
W, H = 1920, 1080


def record(pw, name: str, fn, shot: str | None = None) -> float:
    """Record one scene; returns measured duration in seconds."""
    SEGS.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    ctx = pw.chromium.launch().new_context(
        viewport={"width": W, "height": H},
        record_video_dir=str(SEGS),
        record_video_size={"width": W, "height": H},
    )
    page = ctx.new_page()
    t0 = time.time()
    fn(page)
    if shot:
        page.screenshot(path=str(SHOTS / shot))
    ctx.close()
    webms = sorted(SEGS.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    webms[-1].rename(SEGS / f"{name}.webm")
    return time.time() - t0


def scene_lab(page):
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_selector("text=Strategy Zoo")
    page.wait_for_timeout(8000)


def scene_run(page):
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_selector("text=Strategy Zoo")
    page.get_by_text("MA-Crossover Zoo on Gold (monthly, World Bank)").click()
    page.wait_for_url("**/verdict", timeout=240_000)
    page.wait_for_selector("text=Mirage Score", timeout=240_000)
    page.wait_for_timeout(4000)


def scene_verdict_detail(page):
    page.goto(f"{BASE}/verdict", wait_until="networkidle")
    page.wait_for_timeout(1500)
    pid = page.evaluate(
        "fetch('/api/programs').then(r=>r.json())"
        ".then(j=>j.filter(p=>p.has_analysis)"
        ".sort((a,b)=>b.last_ts-a.last_ts)[0].program_id)")
    page.fill("input[placeholder='program id']", pid)
    page.get_by_role("button", name="Load").click()
    page.wait_for_selector("text=Mirage Score", timeout=240_000)
    page.wait_for_timeout(2500)
    page.mouse.wheel(0, 700)
    page.wait_for_timeout(2500)
    page.mouse.wheel(0, 700)
    page.wait_for_timeout(2500)
    page.mouse.wheel(0, -700)
    page.wait_for_timeout(1500)


def scene_ledger(page):
    page.goto(f"{BASE}/ledger", wait_until="networkidle")
    page.wait_for_selector("text=Ledger")
    page.wait_for_timeout(1500)
    page.locator("button:has-text('trials')").first.click()
    page.wait_for_selector("div.label:has-text('chain head')", timeout=30_000)
    page.wait_for_timeout(3000)
    page.mouse.wheel(0, 600)
    page.wait_for_timeout(2500)


def scene_upload(page):
    page.goto(f"{BASE}/audit", wait_until="networkidle")
    page.wait_for_selector("text=Audit")
    page.wait_for_timeout(1500)
    page.set_input_files("input[type=file]", str(SHOTS / "sample_returns.csv"))
    page.wait_for_timeout(1000)
    page.get_by_text("Audit this backtest").click()
    page.wait_for_selector("text=Mirage Score", timeout=240_000)
    page.wait_for_timeout(3500)


def scene_about(page):
    page.goto(f"{BASE}/about", wait_until="networkidle")
    page.wait_for_timeout(2000)
    for _ in range(4):
        page.mouse.wheel(0, 600)
        page.wait_for_timeout(2000)
    page.mouse.wheel(0, -1200)
    page.wait_for_timeout(1000)


def make_sample_csv():
    rng = np.random.default_rng(3)
    n, cols = 756, 30
    dates = np.datetime64("2023-01-02") + np.arange(n)
    m = rng.normal(0.0004, 0.009, (n, cols))
    m[:, 0] += 0.0012  # lucky winner
    hdr = ",".join(["date"] + [f"strategy_{i}" for i in range(cols)])
    rows = "\n".join(
        f"{d}," + ",".join(f"{x:.6f}" for x in row) for d, row in zip(dates.astype(str), m, strict=False)
    )
    (SHOTS / "sample_returns.csv").write_text(hdr + "\n" + rows)


def main():
    SEGS.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    for old in SEGS.glob("*.webm"):
        old.unlink()
    make_sample_csv()
    durs: dict[str, float] = {}
    with sync_playwright() as pw:
        durs["lab"] = record(pw, "03_lab", scene_lab, shot="01_strategy_lab.png")
        durs["run"] = record(pw, "04_run", scene_run, shot="02_verdict_top.png")
        durs["vd"] = record(pw, "05_verdict", scene_verdict_detail, shot="03_verdict_charts.png")
        durs["ledger"] = record(pw, "06_ledger", scene_ledger, shot="04_ledger.png")
        durs["upload"] = record(pw, "07_upload", scene_upload, shot="05_upload_verdict.png")
        durs["about"] = record(pw, "075_about", scene_about, shot="08_about_scrolled.png")
        ctx = pw.chromium.launch().new_context(viewport={"width": W, "height": H})
        p = ctx.new_page()
        p.goto(f"{BASE}/audit", wait_until="networkidle")
        p.wait_for_selector("text=Audit")
        p.screenshot(path=str(SHOTS / "06_audit_page.png"))
        p.goto(f"{BASE}/about", wait_until="networkidle")
        p.wait_for_timeout(1200)
        p.screenshot(path=str(SHOTS / "07_about_methods.png"))
        p.goto(BASE, wait_until="networkidle")
        p.wait_for_selector("text=Strategy Zoo")
        p.screenshot(path=str(SHOTS / "00_lab_full.png"))
        ctx.close()
    (SEGS / "durations.json").write_text(json.dumps(durs, indent=1))
    print(json.dumps(durs, indent=1))


if __name__ == "__main__":
    main()
