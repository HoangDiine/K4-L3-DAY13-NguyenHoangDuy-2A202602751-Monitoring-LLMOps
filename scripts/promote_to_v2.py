"""
Script thực hiện Promote nhãn 'production' sang Prompt Version 2 trên Langfuse Cloud
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('.env')

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from langfuse import Langfuse

def main():
    configure_utf8_stdio()
    client = Langfuse()

    print("=" * 60)
    print("TIẾN HÀNH PROMOTE PROMPT LÊN VERSION 2")
    print("=" * 60)
    
    p_before = client.get_prompt("day13-chat")
    print(f"Trạng thái hiện tại: Nhãn 'production' đang trỏ vào Version {p_before.version}")

    print("\n>> Đang chuyển nhãn 'production' sang Version 2...")
    client.update_prompt(name="day13-chat", version=2, new_labels=["candidate", "production"])

    p_after = client.get_prompt("day13-chat")
    print(f">> KẾT QUẢ PROMOTE: Nhãn 'production' hiện đã trỏ về Version {p_after.version} ({p_after.labels})")
    print("=" * 60)
    print("HOÀN THÀNH PROMOTE LÊN V2!")

if __name__ == "__main__":
    main()
