from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
import numpy as np

router = APIRouter()
REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_PATH = REPO_ROOT / "data" / "logs.jsonl"


def read_logs_data():
    records = []
    if not LOGS_PATH.exists():
        return records
    with open(LOGS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "ts" in rec:
                    records.append(rec)
            except Exception:
                continue
    return records


@router.get("/api/dashboard-data")
async def get_dashboard_data() -> dict[str, Any]:
    records = read_logs_data()
    if not records:
        return {"ok": False, "message": "No logs found"}

    for r in records:
        r["dt"] = datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))

    # Last 60 minutes relative to max record time
    max_time = max(r["dt"] for r in records)
    min_time = max_time - timedelta(minutes=60)
    window_records = [r for r in records if r["dt"] >= min_time]
    if len(window_records) < 5:
        window_records = records
        min_time = min(r["dt"] for r in records)

    req_received = [r for r in window_records if r.get("event") == "request_received"]
    resp_sent = [r for r in window_records if r.get("event") == "response_sent"]
    req_failed = [r for r in window_records if r.get("event") == "request_failed"]

    # 1. Latency
    latencies = [r.get("latency_ms", 0) for r in resp_sent]
    ttfts = [r.get("ttft_ms", 0) for r in resp_sent]
    times_resp = [r["dt"].strftime("%H:%M:%S") for r in resp_sent]
    p50 = float(np.percentile(latencies, 50)) if latencies else 0.0
    p95 = float(np.percentile(latencies, 95)) if latencies else 0.0
    p99 = float(np.percentile(latencies, 99)) if latencies else 0.0
    ttft_p95 = float(np.percentile(ttfts, 95)) if ttfts else 0.0

    # 2. Traffic
    # group by minute
    traffic_by_min: dict[str, int] = {}
    for r in req_received:
        m_str = r["dt"].strftime("%H:%M")
        traffic_by_min[m_str] = traffic_by_min.get(m_str, 0) + 1

    # 3. Errors
    total_req = len(req_received)
    failed_req = len(req_failed)
    error_rate_pct = round((failed_req / total_req * 100), 2) if total_req > 0 else 0.0
    retrieval_ok = sum(1 for r in resp_sent if r.get("tool_success") is True)
    retrieval_total = sum(1 for r in resp_sent if r.get("tool_success") is not None)
    retrieval_rate_pct = round((retrieval_ok / retrieval_total * 100), 2) if retrieval_total > 0 else 100.0

    # 4. Cost
    costs = [r.get("cost_usd", 0.0) for r in resp_sent]
    cum_costs = [float(c) for c in np.cumsum(costs)] if costs else [0.0]
    total_cost = round(cum_costs[-1], 5) if cum_costs else 0.0

    # 5. Tokens
    tokens_in = [r.get("tokens_in", 0) for r in resp_sent]
    tokens_out = [r.get("tokens_out", 0) for r in resp_sent]
    sum_tokens = sum(tokens_in) + sum(tokens_out)

    # 6. Quality
    quality_scores = [r.get("quality_score", 0.0) for r in resp_sent]
    mean_quality = round(float(np.mean(quality_scores)), 3) if quality_scores else 0.0

    return {
        "ok": True,
        "time_range": f"{min_time.strftime('%H:%M')} – {max_time.strftime('%H:%M')} UTC (Last 60m)",
        "summary": {
            "total_requests": total_req,
            "latency_p95": p95,
            "latency_p50": p50,
            "ttft_p95": ttft_p95,
            "error_rate_pct": error_rate_pct,
            "retrieval_rate_pct": retrieval_rate_pct,
            "total_cost": total_cost,
            "total_tokens": sum_tokens,
            "mean_quality": mean_quality,
        },
        "latency_series": {
            "times": times_resp,
            "latencies": latencies,
            "ttfts": ttfts,
            "threshold": 3000,
        },
        "traffic_series": {
            "minutes": list(traffic_by_min.keys()),
            "counts": list(traffic_by_min.values()),
            "threshold": 1,
        },
        "error_series": {
            "labels": ["Error Rate (%)", "Retrieval Success (%)"],
            "values": [error_rate_pct, retrieval_rate_pct],
            "threshold_error": 2,
            "threshold_retrieval": 90,
        },
        "cost_series": {
            "times": times_resp,
            "cumulative": cum_costs,
            "threshold": 2.5,
        },
        "token_series": {
            "times": times_resp,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "threshold": 50000,
        },
        "quality_series": {
            "times": times_resp,
            "scores": quality_scores,
            "mean": mean_quality,
            "threshold": 0.75,
        },
    }


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_html():
    html_content = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>K4-L3A Day 13 Monitoring & LLMOps — Live Interactive Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
  <style>
    :root {
      --bg: #0e1117;
      --card-bg: #181b1f;
      --border: #2a2e39;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --accent: #58a6ff;
      --green: #3fb950;
      --red: #f85149;
      --yellow: #d29922;
      --purple: #bc8cff;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 24px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    h1 { font-size: 22px; font-weight: 700; color: #fff; }
    .meta { color: var(--text-muted); font-size: 13px; margin-top: 4px; }
    .badge-bar { display: flex; gap: 10px; align-items: center; }
    .badge {
      background: #162c1e;
      color: #7ee787;
      border: 1px solid #238636;
      border-radius: 20px;
      padding: 6px 14px;
      font-size: 13px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .badge-pulse {
      width: 8px; height: 8px; border-radius: 50%; background: #3fb950;
      box-shadow: 0 0 8px #3fb950;
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
    .refresh-btn {
      background: #21262d;
      border: 1px solid #30363d;
      color: #c9d1d9;
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
    }
    .refresh-btn:hover { background: #30363d; }
    
    .grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }
    @media (max-width: 1200px) {
      .grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 768px) {
      .grid { grid-template-columns: 1fr; }
    }
    
    .panel {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      position: relative;
      display: flex;
      flex-direction: column;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }
    .panel-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--accent);
    }
    .panel-unit {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .panel-stat {
      font-size: 20px;
      font-weight: 700;
      color: #fff;
      text-align: right;
    }
    .panel-threshold {
      font-size: 11px;
      color: var(--red);
      margin-top: 2px;
    }
    .chart-box {
      position: relative;
      flex-grow: 1;
      height: 220px;
    }
  </style>
</head>
<body>

  <header>
    <div>
      <h1>K4-L3A Day 13 Monitoring & LLMOps — Live Interactive Dashboard</h1>
      <div class="meta">Học viên: <strong>Nguyễn Hoàng Duy (2A202602751)</strong> | Service: <code>api</code> | Time Range: <span id="timeRangeSpan">60 Phút gần nhất</span> | Refresh: 30s</div>
    </div>
    <div class="badge-bar">
      <div class="badge"><span class="badge-pulse"></span> LIVE REFRESH: 30s</div>
      <button class="refresh-btn" onclick="fetchData()">Làm mới ngay</button>
    </div>
  </header>

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">1. Latency Percentiles & TTFT</div>
          <div class="panel-unit">Đơn vị: Milliseconds (ms)</div>
        </div>
        <div>
          <div class="panel-stat" id="statLatencyP95">-- ms</div>
          <div class="panel-threshold">SLO: P95 &le; 3000ms</div>
        </div>
      </div>
      <div class="chart-box"><canvas id="chartLatency"></canvas></div>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">2. Request Traffic</div>
          <div class="panel-unit">Đơn vị: Requests / minute</div>
        </div>
        <div>
          <div class="panel-stat" id="statTraffic">-- req</div>
          <div class="panel-threshold">Ngưỡng: &ge; 1 req/min</div>
        </div>
      </div>
      <div class="chart-box"><canvas id="chartTraffic"></canvas></div>
    </div>

    <!-- Panel 3: Errors -->
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">3. Error Rate & Retrieval Success</div>
          <div class="panel-unit">Đơn vị: Phần trăm (%)</div>
        </div>
        <div>
          <div class="panel-stat" id="statErrors">0.0%</div>
          <div class="panel-threshold">Ngưỡng: Error &le; 2%</div>
        </div>
      </div>
      <div class="chart-box"><canvas id="chartErrors"></canvas></div>
    </div>

    <!-- Panel 4: Cost -->
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">4. Cost Over Time</div>
          <div class="panel-unit">Đơn vị: USD ($)</div>
        </div>
        <div>
          <div class="panel-stat" id="statCost">$0.00</div>
          <div class="panel-threshold">Ngưỡng: Total &le; $2.50</div>
        </div>
      </div>
      <div class="chart-box"><canvas id="chartCost"></canvas></div>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">5. Input & Output Tokens</div>
          <div class="panel-unit">Đơn vị: Tokens</div>
        </div>
        <div>
          <div class="panel-stat" id="statTokens">--</div>
          <div class="panel-threshold">Ngưỡng: Sum &le; 50,000</div>
        </div>
      </div>
      <div class="chart-box"><canvas id="chartTokens"></canvas></div>
    </div>

    <!-- Panel 6: Quality -->
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">6. Quality Proxy</div>
          <div class="panel-unit">Đơn vị: Score (0.0 đến 1.0)</div>
        </div>
        <div>
          <div class="panel-stat" id="statQuality">--</div>
          <div class="panel-threshold">Ngưỡng: Mean &ge; 0.75</div>
        </div>
      </div>
      <div class="chart-box"><canvas id="chartQuality"></canvas></div>
    </div>
  </div>

  <script>
    let charts = {};

    Chart.defaults.color = '#8b949e';
    Chart.defaults.borderColor = '#2a2e39';
    Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto';

    async function fetchData() {
      try {
        const res = await fetch('/api/dashboard-data');
        const data = await res.json();
        if (!data.ok) return;

        document.getElementById('timeRangeSpan').textContent = data.time_range;
        document.getElementById('statLatencyP95').textContent = data.summary.latency_p95.toFixed(1) + ' ms';
        document.getElementById('statTraffic').textContent = data.summary.total_requests + ' req';
        document.getElementById('statErrors').textContent = data.summary.error_rate_pct.toFixed(1) + '%';
        document.getElementById('statCost').textContent = '$' + data.summary.total_cost.toFixed(4);
        document.getElementById('statTokens').textContent = data.summary.total_tokens.toLocaleString();
        document.getElementById('statQuality').textContent = data.summary.mean_quality.toFixed(2) + ' / 1.0';

        renderLatency(data.latency_series);
        renderTraffic(data.traffic_series);
        renderErrors(data.error_series);
        renderCost(data.cost_series);
        renderTokens(data.token_series);
        renderQuality(data.quality_series);
      } catch (err) {
        console.error('Lỗi nạp dashboard data:', err);
      }
    }

    function renderLatency(d) {
      if (charts.latency) charts.latency.destroy();
      const thresholdData = new Array(d.times.length).fill(3000);
      charts.latency = new Chart(document.getElementById('chartLatency'), {
        type: 'line',
        data: {
          labels: d.times,
          datasets: [
            { label: 'Latency (ms)', data: d.latencies, borderColor: '#388bfd', backgroundColor: '#388bfd', tension: 0.1 },
            { label: 'TTFT (ms)', data: d.ttfts, borderColor: '#79c0ff', backgroundColor: '#79c0ff', tension: 0.1 },
            { label: 'SLO (3000ms)', data: thresholdData, borderColor: '#f85149', borderDash: [6, 4], pointRadius: 0, borderWidth: 2 }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }

    function renderTraffic(d) {
      if (charts.traffic) charts.traffic.destroy();
      const thresholdData = new Array(d.minutes.length).fill(1);
      charts.traffic = new Chart(document.getElementById('chartTraffic'), {
        type: 'bar',
        data: {
          labels: d.minutes,
          datasets: [
            { label: 'Requests / min', data: d.counts, backgroundColor: '#3fb950', borderRadius: 4 },
            { type: 'line', label: 'Threshold (1 req/m)', data: thresholdData, borderColor: '#f85149', borderDash: [6, 4], pointRadius: 0, borderWidth: 2 }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }

    function renderErrors(d) {
      if (charts.errors) charts.errors.destroy();
      charts.errors = new Chart(document.getElementById('chartErrors'), {
        type: 'bar',
        data: {
          labels: d.labels,
          datasets: [{
            label: 'Tỷ lệ (%)',
            data: d.values,
            backgroundColor: ['#2ea043', '#388bfd'],
            borderRadius: 6
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: { y: { max: 120 } }
        }
      });
    }

    function renderCost(d) {
      if (charts.cost) charts.cost.destroy();
      const thresholdData = new Array(d.times.length).fill(2.5);
      charts.cost = new Chart(document.getElementById('chartCost'), {
        type: 'line',
        data: {
          labels: d.times,
          datasets: [
            { label: 'Cumulative Cost ($)', data: d.cumulative, borderColor: '#d29922', backgroundColor: 'rgba(210, 153, 34, 0.2)', fill: true, tension: 0.1 },
            { label: 'Threshold ($2.50)', data: thresholdData, borderColor: '#f85149', borderDash: [6, 4], pointRadius: 0, borderWidth: 2 }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }

    function renderTokens(d) {
      if (charts.tokens) charts.tokens.destroy();
      charts.tokens = new Chart(document.getElementById('chartTokens'), {
        type: 'line',
        data: {
          labels: d.times,
          datasets: [
            { label: 'Tokens In', data: d.tokens_in, borderColor: '#bc8cff', backgroundColor: '#bc8cff', tension: 0.1 },
            { label: 'Tokens Out', data: d.tokens_out, borderColor: '#f0883e', backgroundColor: '#f0883e', tension: 0.1 }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }

    function renderQuality(d) {
      if (charts.quality) charts.quality.destroy();
      const thresholdData = new Array(d.times.length).fill(0.75);
      charts.quality = new Chart(document.getElementById('chartQuality'), {
        type: 'line',
        data: {
          labels: d.times,
          datasets: [
            { label: 'Quality Score', data: d.scores, borderColor: '#7ee787', backgroundColor: '#7ee787', tension: 0.1 },
            { label: 'Threshold (&ge; 0.75)', data: thresholdData, borderColor: '#f85149', borderDash: [6, 4], pointRadius: 0, borderWidth: 2 }
          ]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: { y: { min: 0, max: 1.2 } }
        }
      });
    }

    // Initial load and periodic refresh every 30 seconds
    fetchData();
    setInterval(fetchData, 30000);
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)
