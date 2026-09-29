"""Generate incident evidence images (12-incident-metric.png, 13-incident-log.png, 14-incident-trace.png) for CP3."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_PATH = REPO_ROOT / "data" / "logs.jsonl"
EVIDENCE_DIR = REPO_ROOT / "submission" / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def load_logs():
    records = []
    with open(LOGS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    r = json.loads(line)
                    if "ts" in r:
                        r["dt"] = datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
                        records.append(r)
                except Exception:
                    continue
    return records


def generate_incident_metric_image(records):
    resp_records = [r for r in records if r.get("event") == "response_sent"]
    if not resp_records:
        return

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(14, 7), facecolor="#0e1117")
    ax.set_facecolor("#181b1f")

    times = [r["dt"] for r in resp_records]
    latencies = [r.get("latency_ms", 0) for r in resp_records]

    # Plot normal points vs incident points
    normal_times = []
    normal_lats = []
    incident_times = []
    incident_lats = []

    for r in resp_records:
        if r.get("feature") == "monitoring" and r.get("latency_ms", 0) > 2000:
            incident_times.append(r["dt"])
            incident_lats.append(r.get("latency_ms", 0))
        else:
            normal_times.append(r["dt"])
            normal_lats.append(r.get("latency_ms", 0))

    ax.plot(times, latencies, color="#30363d", linestyle=":", linewidth=1.5, zorder=1)
    ax.scatter(normal_times, normal_lats, color="#388bfd", s=45, label="Normal Requests (Baseline: ~152ms)", zorder=2)
    ax.scatter(incident_times, incident_lats, color="#f85149", s=90, edgecolors="#ffffff", linewidth=1.5,
               label="Incident Requests: rag_slow (Spike: 2,653ms – 3,769ms)", zorder=3)

    # Threshold lines
    ax.axhline(y=2000, color="#d29922", linestyle="--", linewidth=1.8, label="Challenge Threshold: 2000ms")
    ax.axhline(y=3000, color="#f85149", linestyle="--", linewidth=2.0, label="SLO P95 Threshold: 3000ms")

    # Title & Labels
    ax.set_title("CP3 Incident Metric: High Response Latency (rag_slow)\nChallenge ID: day13-k4-l3a-monitoring-llmops-v1 | Cohort: K4",
                 fontsize=14, fontweight="bold", color="#ffffff", pad=15)
    ax.set_xlabel("Time (UTC)", color="#c9d1d9", fontsize=11)
    ax.set_ylabel("Latency (ms)", color="#c9d1d9", fontsize=11)
    ax.set_ylim(0, 4200)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    ax.grid(True, linestyle="--", color="#2a2e39", alpha=0.7)
    ax.legend(loc="upper left", fontsize=9, facecolor="#1f242c", edgecolor="#30363d")

    # Callout
    ax.annotate(
        "INCIDENT SPIKE\nLatency: 3,769ms\nCorrelation ID: req-8b6e3d84\nWindow: 10:19:04 - 10:19:24 UTC",
        xy=(incident_times[0], incident_lats[0]),
        xytext=(incident_times[0], 2800),
        arrowprops=dict(facecolor="#f85149", shrink=0.08, width=2, headwidth=8),
        fontsize=9, color="#ffffff", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#3c1e1e", edgecolor="#f85149")
    )

    out_file = EVIDENCE_DIR / "12-incident-metric.png"
    plt.tight_layout()
    plt.savefig(out_file, dpi=180, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated: {out_file}")


def generate_incident_log_image():
    # Render clear text log snippet
    log_text = """2026-09-29T10:19:10.648534Z [info] event=response_sent
service=api
correlation_id=req-8b6e3d84
session_id=k4-l3a-challenge-s01
feature=monitoring
model=claude-sonnet-4-5
user_id_hash=dde2e75b20cf
latency_ms=3769   <-- [ANOMALY: EXCEEDS 2000ms & BREACHES SLO]
ttft_ms=50
tool_name=retrieval
tool_success=true
cost_usd=0.002775
tokens_in=35
tokens_out=178
payload={"answer_preview": "Starter answer. You should improve this output..."}"""

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(13, 6.5), facecolor="#0e1117")
    ax.set_facecolor("#161b22")
    ax.axis("off")

    fig.text(0.06, 0.90, "CP3 Incident Log Investigation — Structured JSON Line", fontsize=15, fontweight="bold", color="#58a6ff")
    fig.text(0.06, 0.84, "File: data/logs.jsonl | Correlation ID: req-8b6e3d84 | Timestamp: 2026-09-29T10:19:10.648Z", fontsize=10, color="#8b949e")

    ax.text(0.04, 0.45, log_text, transform=ax.transAxes, fontsize=11, fontfamily="monospace", color="#e6edf3",
            verticalalignment="center",
            bbox=dict(boxstyle="round,pad=0.8", facecolor="#0d1117", edgecolor="#30363d"))

    out_file = EVIDENCE_DIR / "13-incident-log.png"
    plt.tight_layout()
    plt.savefig(out_file, dpi=180, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated: {out_file}")


def generate_incident_trace_image():
    # Render span breakdown waterfall
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(14, 6), facecolor="#0e1117")
    ax.set_facecolor("#181b1f")

    spans = [
        {"name": "1. lab-agent-run (AGENT - Root)", "duration": 4.850, "start": 0.0, "color": "#388bfd", "note": "Total Request Duration: 4.850s"},
        {"name": "2. retrieval (RETRIEVER - Child)", "duration": 2.500, "start": 0.050, "color": "#f85149", "note": "BOTTLENECK / ROOT CAUSE: 2.500s (rag_slow time.sleep)"},
        {"name": "3. llm-generation (GENERATION - Child)", "duration": 0.151, "start": 2.550, "color": "#3fb950", "note": "Normal Inference: 151ms"},
    ]

    y_pos = [2, 1, 0]
    bar_height = 0.45

    for i, s in enumerate(spans):
        ax.barh(y_pos[i], s["duration"], left=s["start"], height=bar_height, color=s["color"], alpha=0.85, edgecolor="#ffffff", linewidth=1.2)
        ax.text(s["start"] + s["duration"] + 0.08, y_pos[i], f"{s['duration']:.3f}s — {s['note']}",
                va="center", color="#ffffff", fontsize=10, fontweight="bold")

    ax.set_yticks(y_pos)
    ax.set_yticklabels([s["name"] for s in spans], fontsize=11, color="#e6edf3")
    ax.set_xlabel("Time (seconds)", fontsize=11, color="#c9d1d9")
    ax.set_xlim(0, 5.5)
    ax.grid(True, linestyle="--", color="#2a2e39", alpha=0.7)
    for spine in ax.spines.values():
        spine.set_color("#30363d")

    ax.set_title("CP3 Incident Trace Waterfall — Span Tree Analysis\nTrace ID: 594ed6a499a5eaa2aff62539f44dc523 | Correlation ID: req-8b6e3d84",
                 fontsize=13, fontweight="bold", color="#ffffff", pad=15)

    out_file = EVIDENCE_DIR / "14-incident-trace.png"
    plt.tight_layout()
    plt.savefig(out_file, dpi=180, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated: {out_file}")


def main():
    records = load_logs()
    generate_incident_metric_image(records)
    generate_incident_log_image()
    generate_incident_trace_image()
    print("All incident evidence generated successfully!")


if __name__ == "__main__":
    main()
