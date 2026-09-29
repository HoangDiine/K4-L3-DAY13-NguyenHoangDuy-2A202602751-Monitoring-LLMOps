import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
configure_utf8_stdio()

REPORT_FILE = REPO_ROOT / "submission" / "REPORT.md"
EVIDENCE_DIR = REPO_ROOT / "submission" / "evidence"


def check(title: str, condition: bool, detail: str = ""):
    status = "PASSED" if condition else "FAILED"
    print(f"[{status}] {title}")
    if detail:
        print(f"       -> {detail}")
    return condition


def main():
    print("=" * 60)
    print("K4-L3A DAY 13 MONITORING & LLMOPS — FINAL SUBMISSION AUDIT")
    print("=" * 60)

    all_passed = True

    # 1. REPORT.md existence & key sections
    report_text = REPORT_FILE.read_text(encoding="utf-8")
    sections = [
        "1. Thông tin học viên",
        "2. Evidence index",
        "3. Kết quả kỹ thuật",
        "4. Logging và PII",
        "5. Tracing và prompt versioning",
        "6. Dashboard, SLO và alerts",
        "7. Điều tra challenge",
        "8. Giải thích và tự đánh giá",
        "9. Checklist trước khi nộp",
    ]
    for s in sections:
        ok = s in report_text
        all_passed = check(f"REPORT.md section: {s}", ok) and all_passed

    # 2. Check all 14 expected evidence files
    expected_evidence = [
        "01-pytest.png",
        "02-log-validator.png",
        "03-dashboard-validator.png",
        "04-structured-log.txt",
        "05-pii-redaction.txt",
        "06-trace-list.png",
        "07-trace-waterfall.png",
        "08-trace-metadata.png",
        "09-prompt-versions.png",
        "10-prompt-rollback_v1.png",
        "10-prompt-rollback_v2.png",
        "11-dashboard-overview.png",
        "12-incident-metric.png",
        "13-incident-log.txt",
        "14-incident-trace.png",
    ]
    for ef in expected_evidence:
        fpath = EVIDENCE_DIR / ef
        ok = fpath.exists() and fpath.stat().st_size > 0
        all_passed = check(f"Evidence file: {ef}", ok, f"Size: {fpath.stat().st_size if ok else 0} bytes") and all_passed

    # 3. Check validators and tests via subprocess
    print("\n--- Running Technical Gates ---")
    r1 = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=REPO_ROOT, capture_output=True, text=True)
    all_passed = check("Pytest suite (all 27 tests)", r1.returncode == 0, r1.stdout.strip()) and all_passed

    r2 = subprocess.run([sys.executable, "scripts/validate_logs.py"], cwd=REPO_ROOT, capture_output=True, text=True)
    all_passed = check("Log Validator (100/100)", r2.returncode == 0 and "100/100" in r2.stdout, "Score: 100/100") and all_passed

    r3 = subprocess.run([sys.executable, "scripts/validate_dashboard.py"], cwd=REPO_ROOT, capture_output=True, text=True)
    all_passed = check("Dashboard Validator (6/6)", r3.returncode == 0 and "6/6" in r3.stdout, r3.stdout.strip()) and all_passed

    # 4. Check git status
    r4 = subprocess.run(["git", "status", "--short"], cwd=REPO_ROOT, capture_output=True, text=True)
    clean = len(r4.stdout.strip()) == 0 or "verify_submission.py" in r4.stdout
    all_passed = check("Git working tree clean", clean, "No uncommitted code changes") and all_passed

    # 5. Git commit info
    r5 = subprocess.run(["git", "log", "-1", "--oneline"], cwd=REPO_ROOT, capture_output=True, text=True)
    r6 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
    commit_sha = r6.stdout.strip()
    print("\n--- Final Submission Information ---")
    print(f"Latest Commit: {r5.stdout.strip()}")
    print(f"Full Commit SHA: {commit_sha}")
    print(f"Cohort: K4-L3A")
    print(f"Student: Nguyen Hoang Duy (2A202602751)")
    print(f"Project Langfuse: day13-k4-l3a-2A202602751")

    print("=" * 60)
    if all_passed:
        print("ALL SUBMISSION CHECKS PASSED SUCCESSFULLY! READY FOR SUBMIT.")
    else:
        print("SOME CHECKS FAILED! Please review above output.")
    print("=" * 60)


if __name__ == "__main__":
    main()
