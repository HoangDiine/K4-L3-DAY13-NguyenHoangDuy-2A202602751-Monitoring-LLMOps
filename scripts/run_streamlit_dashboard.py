"""Streamlit Dashboard for K4-L3A Day 13 Monitoring & LLMOps.
Run with:
    streamlit run scripts/run_streamlit_dashboard.py
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="K4-L3A Day 13 Monitoring & LLMOps Dashboard",
    page_icon="📊",
    layout="wide",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_PATH = REPO_ROOT / "data" / "logs.jsonl"


def load_logs():
    records = []
    if not LOGS_PATH.exists():
        return records
    with open(LOGS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    r = json.loads(line)
                    if "ts" in r:
                        r["datetime"] = datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
                        records.append(r)
                except Exception:
                    continue
    return records


st.title("📊 K4-L3A Day 13 Monitoring & LLMOps — Live Dashboard")
st.caption("Student: Nguyễn Hoàng Duy (2A202602751) | Service: api | Time Range: Last 60 Minutes")

records = load_logs()
if not records:
    st.warning("Chưa có log trong data/logs.jsonl")
    st.stop()

# Time range: last 60m
max_t = max(r["datetime"] for r in records)
min_t = max_t - timedelta(minutes=60)
win = [r for r in records if r["datetime"] >= min_t]
if len(win) < 5:
    win = records

req_rec = [r for r in win if r.get("event") == "request_received"]
resp_sent = [r for r in win if r.get("event") == "response_sent"]
req_fail = [r for r in win if r.get("event") == "request_failed"]

# Row 1: KPI Summary cards
c1, c2, c3, c4, c5, c6 = st.columns(6)
latencies = [r.get("latency_ms", 0) for r in resp_sent]
ttfts = [r.get("ttft_ms", 0) for r in resp_sent]
p95 = np.percentile(latencies, 95) if latencies else 0
c1.metric("P95 Latency", f"{p95:.1f} ms", delta="SLO <= 3000ms" if p95 <= 3000 else "EXCEEDED", delta_color="normal" if p95 <= 3000 else "inverse")
c2.metric("Total Requests", f"{len(req_rec)} req")
err_rate = (len(req_fail) / len(req_rec) * 100) if req_rec else 0
c3.metric("Error Rate", f"{err_rate:.1f}%", delta="<= 2%" if err_rate <= 2 else "HIGH", delta_color="normal" if err_rate <= 2 else "inverse")
total_cost = sum(r.get("cost_usd", 0) for r in resp_sent)
c4.metric("Cost USD", f"${total_cost:.4f}", delta="<= $2.50" if total_cost <= 2.5 else "HIGH")
tot_tokens = sum(r.get("tokens_in", 0) + r.get("tokens_out", 0) for r in resp_sent)
c5.metric("Total Tokens", f"{tot_tokens:,}", delta="<= 50,000")
mean_q = np.mean([r.get("quality_score", 0) for r in resp_sent]) if resp_sent else 0
c6.metric("Quality Proxy", f"{mean_q:.2f} / 1.0", delta=">= 0.75" if mean_q >= 0.75 else "LOW")

st.markdown("---")

col_left, col_mid, col_right = st.columns(3)

with col_left:
    st.subheader("1. Latency & TTFT (ms)")
    st.caption("Threshold: P95 <= 3000 ms")
    if resp_sent:
        df_lat = pd.DataFrame({
            "Time": [r["datetime"] for r in resp_sent],
            "Latency": latencies,
            "TTFT": ttfts,
            "Threshold": 3000
        }).set_index("Time")
        st.line_chart(df_lat)

    st.subheader("4. Cost Over Time (USD)")
    st.caption("Threshold: Total <= $2.50")
    if resp_sent:
        df_cost = pd.DataFrame({
            "Time": [r["datetime"] for r in resp_sent],
            "Cumulative Cost": np.cumsum([r.get("cost_usd", 0) for r in resp_sent]),
            "Threshold": 2.5
        }).set_index("Time")
        st.line_chart(df_cost)

with col_mid:
    st.subheader("2. Request Traffic (req/min)")
    st.caption("Threshold: Rate >= 1 req/min")
    if req_rec:
        t_counts = {}
        for r in req_rec:
            m = r["datetime"].strftime("%H:%M")
            t_counts[m] = t_counts.get(m, 0) + 1
        df_traf = pd.DataFrame(list(t_counts.items()), columns=["Minute", "Requests"]).set_index("Minute")
        st.bar_chart(df_traf)

    st.subheader("5. Input & Output Tokens")
    st.caption("Threshold: Sum <= 50,000")
    if resp_sent:
        df_tok = pd.DataFrame({
            "Time": [r["datetime"] for r in resp_sent],
            "Tokens In": [r.get("tokens_in", 0) for r in resp_sent],
            "Tokens Out": [r.get("tokens_out", 0) for r in resp_sent],
        }).set_index("Time")
        st.area_chart(df_tok)

with col_right:
    st.subheader("3. Error Rate & Retrieval (%)")
    st.caption("Threshold: Error <= 2%, Retrieval >= 90%")
    retrieval_ok = sum(1 for r in resp_sent if r.get("tool_success") is True)
    retrieval_pct = (retrieval_ok / len(resp_sent) * 100) if resp_sent else 100
    df_err = pd.DataFrame({
        "Metric": ["Error Rate %", "Retrieval Success %"],
        "Value": [err_rate, retrieval_pct]
    }).set_index("Metric")
    st.bar_chart(df_err)

    st.subheader("6. Quality Proxy (0..1)")
    st.caption("Threshold: Mean >= 0.75")
    if resp_sent:
        df_q = pd.DataFrame({
            "Time": [r["datetime"] for r in resp_sent],
            "Quality Score": [r.get("quality_score", 0) for r in resp_sent],
            "Threshold": 0.75
        }).set_index("Time")
        st.line_chart(df_q)
