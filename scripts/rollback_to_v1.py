"""
Script thực hiện Rollback nhãn 'production' về Prompt Version 1 trên Langfuse Cloud
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
    print("TIẾN HÀNH ROLLBACK PROMPT TRÊN LANGFUSE CLOUD")
    print("=" * 60)
    
    # Lấy thông tin hiện tại
    p_before = client.get_prompt("day13-chat")
    print(f"Trạng thái hiện tại: Nhãn 'production' đang trỏ vào Version {p_before.version}")

    # Thực hiện Rollback nhãn 'production' về Version 1
    print("\n>> Đang chuyển nhãn 'production' về Version 1...")
    client.update_prompt(name="day13-chat", version=1, new_labels=["baseline", "production"])

    # Xác nhận lại
    p_after = client.get_prompt("day13-chat")
    print(f">> KẾT QUẢ ROLLBACK: Nhãn 'production' hiện đã trỏ về Version {p_after.version} ({p_after.labels})")
    print("=" * 60)
    print("HOÀN THÀNH ROLLBACK AN TOÀN!")

if __name__ == "__main__":
    main()
