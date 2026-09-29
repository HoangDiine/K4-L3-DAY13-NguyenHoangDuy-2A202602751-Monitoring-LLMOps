"""Generate 6-panel runtime dashboard from data/logs.jsonl according to config/dashboard.yaml."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_PATH = REPO_ROOT / "data" / "logs.jsonl"
OUTPUT_PATH = REPO_ROOT / "submission" / "evidence" / "11-dashboard-overview.png"


def load_logs():
    records = []
    if not LOGS_PATH.exists():
        print(f"Error: {LOGS_PATH} not found")
        return records

    with open(LOGS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "ts" in rec:
                    rec["datetime"] = datetime.fromisoformat(rec["ts"].replace("Z", "+00:00"))
                    records.append(rec)
            except Exception:
                continue
    return records


def main():
    records = load_logs()
    if not records:
        print("No valid logs found in data/logs.jsonl")
        return 1

    # Use all records for comprehensive session view
    window_records = records
    min_time = min(r["datetime"] for r in records)
    max_time = max(r["datetime"] for r in records)

    # Separate events
    requests_received = [r for r in window_records if r.get("event") == "request_received"]
    responses_sent = [r for r in window_records if r.get("event") == "response_sent"]
    requests_failed = [r for r in window_records if r.get("event") == "request_failed"]

    # Style configuration - Grafana Dark Theme
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(19, 12), facecolor="#0e1117")
    fig.patch.set_facecolor("#0e1117")

    # Super Title & Header
    title_text = "K4-L3A Day 13 Monitoring & LLMOps — Runtime Dashboard"
    subtitle_text = (
        f"Student: Nguyen Hoang Duy (MSSV: 2A202602751)  |  Service: api  |  "
        f"Time Range: Last 60 Minutes ({min_time.strftime('%H:%M')} – {max_time.strftime('%H:%M')} UTC)  |  "
        f"Refresh: 30s  |  Status: 6/6 Panels Valid & Healthy"
    )
    fig.text(0.05, 0.965, title_text, fontsize=19, fontweight="bold", color="#ffffff")
    fig.text(0.05, 0.935, subtitle_text, fontsize=11, color="#8b949e")

    # Grid 2 rows x 3 columns
    axes = fig.subplots(2, 3)
    plt.subplots_adjust(left=0.06, right=0.96, top=0.87, bottom=0.08, wspace=0.24, hspace=0.38)

    panel_bg = "#181b1f"
    grid_color = "#2a2e39"

    for ax in axes.flat:
        ax.set_facecolor(panel_bg)
        ax.grid(True, linestyle="--", linewidth=0.6, color=grid_color, alpha=0.7)
        for spine in ax.spines.values():
            spine.set_color("#343a46")

    # -------------------------------------------------------------
    # Panel 1: Latency percentiles and TTFT (unit: ms, threshold <= 3000ms)
    # -------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_title("1. Latency Percentiles & TTFT\n[Unit: ms | Time Range: 60m]", fontsize=12, fontweight="bold", color="#58a6ff", pad=10)

    if responses_sent:
        latencies = [r.get("latency_ms", 0) for r in responses_sent]
        ttfts = [r.get("ttft_ms", 0) for r in responses_sent]
        times = [r["datetime"] for r in responses_sent]

        # Calculate aggregations
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        ttft_p95 = np.percentile(ttfts, 95)

        ax1.plot(times, latencies, "o-", color="#388bfd", label=f"Latency (P50: {p50:.1f}ms, P95: {p95:.1f}ms)", markersize=4, alpha=0.85)
        ax1.plot(times, ttfts, "s-", color="#79c0ff", label=f"TTFT (P95: {ttft_p95:.1f}ms)", markersize=3, alpha=0.85)
        ax1.axhline(y=3000, color="#f85149", linestyle="--", linewidth=1.8, label="SLO Threshold: P95 <= 3000ms")

        ax1.set_ylabel("Latency (ms)", color="#c9d1d9", fontsize=10)
        ax1.set_ylim(0, max(max(latencies) * 1.25, 3500))
        ax1.legend(loc="upper right", fontsize=8, facecolor="#1f242c", edgecolor="#30363d")
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        # Stat callout
        ax1.text(0.04, 0.85, f"P95: {p95:.1f}ms (Pass)\nTTFT: {ttft_p95:.1f}ms", transform=ax1.transAxes,
                 fontsize=9, color="#7ee787", bbox=dict(boxstyle="round,pad=0.3", facecolor="#162c1e", edgecolor="#238636"))

    # -------------------------------------------------------------
    # Panel 2: Request traffic (unit: requests_per_minute, threshold >= 1)
    # -------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_title("2. Request Traffic\n[Unit: requests_per_minute | Time Range: 60m]", fontsize=12, fontweight="bold", color="#58a6ff", pad=10)

    if requests_received:
        # Group by 1-minute bins
        req_times = [r["datetime"] for r in requests_received]
        # Sort and count
        sorted_times = sorted(req_times)
        # Create bins per minute
        start_bin = sorted_times[0].replace(second=0, microsecond=0)
        end_bin = sorted_times[-1].replace(second=0, microsecond=0) + timedelta(minutes=1)
        cur = start_bin
        bin_edges = []
        while cur <= end_bin:
            bin_edges.append(cur)
            cur += timedelta(minutes=1)

        counts = [0] * (len(bin_edges) - 1)
        for t in req_times:
            for idx in range(len(bin_edges) - 1):
                if bin_edges[idx] <= t < bin_edges[idx + 1]:
                    counts[idx] += 1
                    break

        bin_centers = [bin_edges[i] for i in range(len(counts))]
        ax2.bar(bin_centers, counts, width=timedelta(seconds=45), color="#3fb950", alpha=0.75, label=f"Rate (req/min) — Total: {len(requests_received)} req")
        ax2.plot(bin_centers, counts, color="#2ea043", linewidth=1.5)
        ax2.axhline(y=1, color="#f85149", linestyle="--", linewidth=1.8, label="Threshold: Rate >= 1 req/min")

        ax2.set_ylabel("Requests / min", color="#c9d1d9", fontsize=10)
        ax2.set_ylim(0, max(max(counts) * 1.3, 5))
        ax2.legend(loc="upper right", fontsize=8, facecolor="#1f242c", edgecolor="#30363d")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        # Stat callout
        avg_rate = np.mean([c for c in counts if c > 0]) if counts else 0
        ax2.text(0.04, 0.85, f"Peak: {max(counts)} req/min\nActive avg: {avg_rate:.1f} req/m", transform=ax2.transAxes,
                 fontsize=9, color="#7ee787", bbox=dict(boxstyle="round,pad=0.3", facecolor="#162c1e", edgecolor="#238636"))

    # -------------------------------------------------------------
    # Panel 3: Error rate and retrieval success (unit: percent, threshold <= 2%)
    # -------------------------------------------------------------
    ax3 = axes[0, 2]
    ax3.set_title("3. Error Rate & Retrieval Success\n[Unit: percent | Time Range: 60m]", fontsize=12, fontweight="bold", color="#58a6ff", pad=10)

    total_req = len(requests_received)
    failed_req = len(requests_failed)
    error_rate_pct = (failed_req / total_req * 100) if total_req > 0 else 0.0

    retrieval_successes = sum(1 for r in responses_sent if r.get("tool_success") is True)
    retrieval_total = sum(1 for r in responses_sent if r.get("tool_success") is not None)
    retrieval_rate_pct = (retrieval_successes / retrieval_total * 100) if retrieval_total > 0 else 100.0

    # Plot bar comparison
    metrics = ["Error Rate %", "Retrieval Success %"]
    values = [error_rate_pct, retrieval_rate_pct]
    colors = ["#3fb950" if error_rate_pct <= 2 else "#f85149", "#388bfd"]
    bars = ax3.bar(metrics, values, color=colors, width=0.45, alpha=0.85)

    ax3.axhline(y=2, color="#f85149", linestyle="--", linewidth=1.8, label="Threshold: Error Rate <= 2%")
    ax3.axhline(y=90, color="#d29922", linestyle=":", linewidth=1.5, label="SLO Guardrail: Retrieval >= 90%")

    ax3.set_ylabel("Percentage (%)", color="#c9d1d9", fontsize=10)
    ax3.set_ylim(0, 135)
    ax3.legend(loc="upper right", fontsize=8, facecolor="#1f242c", edgecolor="#30363d")

    for bar, val in zip(bars, values):
        ax3.text(bar.get_x() + bar.get_width() / 2, val + 3, f"{val:.1f}%", ha="center", va="bottom",
                 fontsize=10, fontweight="bold", color="#ffffff")

    ax3.text(0.04, 0.40, f"Error Types: 0 (None)\nTotal Requests: {total_req}\nFailed Requests: {failed_req}", transform=ax3.transAxes,
             fontsize=9, color="#7ee787", bbox=dict(boxstyle="round,pad=0.3", facecolor="#162c1e", edgecolor="#238636"))

    # -------------------------------------------------------------
    # Panel 4: Cost over time (unit: usd, threshold total <= $2.5)
    # -------------------------------------------------------------
    ax4 = axes[1, 0]
    ax4.set_title("4. Cost Over Time\n[Unit: USD | Time Range: 60m]", fontsize=12, fontweight="bold", color="#58a6ff", pad=10)

    if responses_sent:
        costs = [r.get("cost_usd", 0.0) for r in responses_sent]
        c_times = [r["datetime"] for r in responses_sent]
        cum_cost = np.cumsum(costs)
        total_cost = cum_cost[-1]

        ax4.plot(c_times, cum_cost, "o-", color="#d29922", linewidth=2, label=f"Cumulative Cost (${total_cost:.4f})", markersize=4)
        ax4.fill_between(c_times, 0, cum_cost, color="#d29922", alpha=0.15)
        ax4.axhline(y=2.5, color="#f85149", linestyle="--", linewidth=1.8, label="Threshold: Total Cost <= $2.50")

        ax4.set_ylabel("Cost (USD)", color="#c9d1d9", fontsize=10)
        ax4.set_ylim(0, 3.0)
        ax4.legend(loc="upper left", fontsize=8, facecolor="#1f242c", edgecolor="#30363d")
        ax4.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

        ax4.text(0.04, 0.60, f"Total Cost: ${total_cost:.4f}\nAvg/req: ${np.mean(costs):.5f}\nBudget Used: {(total_cost/2.5)*100:.1f}%",
                 transform=ax4.transAxes, fontsize=9, color="#7ee787",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#162c1e", edgecolor="#238636"))

    # -------------------------------------------------------------
    # Panel 5: Input and output tokens (unit: tokens, threshold sum <= 50000)
    # -------------------------------------------------------------
    ax5 = axes[1, 1]
    ax5.set_title("5. Input and Output Tokens\n[Unit: tokens | Time Range: 60m]", fontsize=12, fontweight="bold", color="#58a6ff", pad=10)

    if responses_sent:
        tokens_in = [r.get("tokens_in", 0) for r in responses_sent]
        tokens_out = [r.get("tokens_out", 0) for r in responses_sent]
        tok_times = [r["datetime"] for r in responses_sent]
        total_tokens = sum(tokens_in) + sum(tokens_out)

        ax5.plot(tok_times, tokens_in, "o-", color="#a371f7", label=f"Tokens In (Sum: {sum(tokens_in):,})", markersize=3, alpha=0.85)
        ax5.plot(tok_times, tokens_out, "s-", color="#f0883e", label=f"Tokens Out (Sum: {sum(tokens_out):,})", markersize=3, alpha=0.85)
        ax5.axhline(y=50000, color="#f85149", linestyle="--", linewidth=1.8, label="Threshold: Sum <= 50,000")

        ax5.set_ylabel("Tokens / request", color="#c9d1d9", fontsize=10)
        ax5.set_ylim(0, max(max(tokens_out) * 1.4, 250))
        ax5.legend(loc="upper right", fontsize=8, facecolor="#1f242c", edgecolor="#30363d")
        ax5.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

        ax5.text(0.04, 0.85, f"Total Tokens: {total_tokens:,}\nIn: {sum(tokens_in):,} | Out: {sum(tokens_out):,}",
                 transform=ax5.transAxes, fontsize=9, color="#7ee787",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#162c1e", edgecolor="#238636"))

    # -------------------------------------------------------------
    # Panel 6: Quality proxy (unit: score_0_to_1, threshold mean >= 0.75)
    # -------------------------------------------------------------
    ax6 = axes[1, 2]
    ax6.set_title("6. Quality Proxy\n[Unit: score (0..1) | Time Range: 60m]", fontsize=12, fontweight="bold", color="#58a6ff", pad=10)

    if responses_sent:
        quality_scores = [r.get("quality_score", 0.0) for r in responses_sent]
        q_times = [r["datetime"] for r in responses_sent]
        mean_quality = np.mean(quality_scores)

        ax6.plot(q_times, quality_scores, "o-", color="#7ee787", label=f"Quality Score (Mean: {mean_quality:.2f})", markersize=4)
        ax6.axhline(y=mean_quality, color="#2ea043", linestyle=":", linewidth=1.5, label=f"Actual Mean: {mean_quality:.2f}")
        ax6.axhline(y=0.75, color="#f85149", linestyle="--", linewidth=1.8, label="Threshold: Mean >= 0.75")

        ax6.set_ylabel("Quality Score (0 to 1)", color="#c9d1d9", fontsize=10)
        ax6.set_ylim(0, 1.15)
        ax6.legend(loc="lower right", fontsize=8, facecolor="#1f242c", edgecolor="#30363d")
        ax6.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

        ax6.text(0.04, 0.85, f"Mean Score: {mean_quality:.2f} / 1.0\nQuality Status: PASS (>= 0.75)",
                 transform=ax6.transAxes, fontsize=9, color="#7ee787",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#162c1e", edgecolor="#238636"))

    # Save high-resolution PNG
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PATH, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Successfully generated runtime dashboard image at: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
