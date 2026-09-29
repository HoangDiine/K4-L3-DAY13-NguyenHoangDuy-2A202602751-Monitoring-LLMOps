"""
Script so sánh và kiểm thử Prompt Version 1 (baseline) vs Version 2 (candidate)
Yêu cầu của CP2:
  1. Chạy cùng một input message với LANGFUSE_PROMPT_LABEL=baseline và candidate.
  2. Kiểm tra prompt_name, prompt_label, prompt_version và Trace ID tương ứng.
"""
import os
import sys
from pathlib import Path

# Nạp biến môi trường từ .env
from dotenv import load_dotenv
load_dotenv('.env')

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.agent import LabAgent
from app.cli import configure_utf8_stdio
from app.prompt_management import resolve_prompt
from app.tracing import get_langfuse_client

def main():
    configure_utf8_stdio()
    client = get_langfuse_client()
    agent = LabAgent()
    
    test_question = "Explain why metrics traces and logs work together"
    print("=" * 80)
    print(f"CÂU HỎI THỬ NGHIỆM (INPUT): '{test_question}'")
    print("=" * 80)

    # -------------------------------------------------------------
    # 1. TEST PROMPT VERSION 1 (Nhãn: baseline)
    # -------------------------------------------------------------
    print("\n[BƯỚC 1] Đang chạy với LANGFUSE_PROMPT_LABEL = 'baseline' (Version 1)...")
    os.environ["LANGFUSE_PROMPT_LABEL"] = "baseline"
    
    # Resolve prompt để xem nội dung template v1
    pv1 = resolve_prompt(client, feature="qa", docs=["Doc A: Metrics show symptoms."], message=test_question, enabled=True)
    
    res1 = agent.run(
        user_id="user_test_v1",
        feature="qa",
        session_id="session_test_v1",
        message=test_question,
        correlation_id="req-test-prompt-v1"
    )
    if hasattr(client, "flush"):
        client.flush()

    print(f"  + Prompt Name   : {pv1.name}")
    print(f"  + Prompt Label  : {pv1.label}")
    print(f"  + Prompt Version: {pv1.version}")
    print(f"  + Prompt Source : {pv1.source}")
    print(f"  + Prompt Content:\n'''\n{pv1.text}\n'''")
    print(f"  + Latency       : {res1.latency_ms}ms")
    print(f"  + Tokens In/Out : {res1.tokens_in} / {res1.tokens_out}")
    print(f"  + Cost USD      : ${res1.cost_usd}")

    # -------------------------------------------------------------
    # 2. TEST PROMPT VERSION 2 (Nhãn: candidate)
    # -------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[BƯỚC 2] Đang chạy với LANGFUSE_PROMPT_LABEL = 'candidate' (Version 2)...")
    os.environ["LANGFUSE_PROMPT_LABEL"] = "candidate"
    
    # Resolve prompt để xem nội dung template v2
    pv2 = resolve_prompt(client, feature="qa", docs=["Doc A: Metrics show symptoms."], message=test_question, enabled=True)
    
    res2 = agent.run(
        user_id="user_test_v2",
        feature="qa",
        session_id="session_test_v2",
        message=test_question,
        correlation_id="req-test-prompt-v2"
    )
    if hasattr(client, "flush"):
        client.flush()

    print(f"  + Prompt Name   : {pv2.name}")
    print(f"  + Prompt Label  : {pv2.label}")
    print(f"  + Prompt Version: {pv2.version}")
    print(f"  + Prompt Source : {pv2.source}")
    print(f"  + Prompt Content:\n'''\n{pv2.text}\n'''")
    print(f"  + Latency       : {res2.latency_ms}ms")
    print(f"  + Tokens In/Out : {res2.tokens_in} / {res2.tokens_out}")
    print(f"  + Cost USD      : ${res2.cost_usd}")

    # -------------------------------------------------------------
    # 3. BẢNG SO SÁNH ĐỐI CHỨNG
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("BẢNG SO SÁNH V1 (BASELINE) VS V2 (CANDIDATE)")
    print("=" * 80)
    print(f"{'Tiêu chí':<20} | {'Version 1 (Baseline)':<25} | {'Version 2 (Candidate)':<25}")
    print("-" * 75)
    print(f"{'Version':<20} | {pv1.version:<25} | {pv2.version:<25}")
    print(f"{'Label':<20} | {pv1.label:<25} | {pv2.label:<25}")
    print(f"{'Correlation ID':<20} | {'req-test-prompt-v1':<25} | {'req-test-prompt-v2':<25}")
    print(f"{'Tokens In':<20} | {res1.tokens_in:<25} | {res2.tokens_in:<25}")
    print(f"{'Chi phí':<20} | ${res1.cost_usd:<24} | ${res2.cost_usd:<24}")
    print(f"{'Độ dài Prompt':<20} | {len(pv1.text):<25} | {len(pv2.text):<25}")
    print("=" * 80)
    print(">> Đã hoàn thành so sánh V1 vs V2! Cả 2 traces đã được đồng bộ lên Langfuse Cloud.")

if __name__ == "__main__":
    main()
