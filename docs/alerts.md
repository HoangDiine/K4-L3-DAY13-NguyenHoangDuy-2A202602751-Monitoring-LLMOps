# Runbook Hướng dẫn Xử lý Alerts

Mỗi alert trong hệ thống được thiết kế theo nguyên tắc symptom-based dựa trên SLO hoặc trải nghiệm trực tiếp của người dùng cuối.

---

## Alert 1: High Response Latency

- **Tên:** HighResponseLatencyP95
- **Severity:** warning
- **Duration:** 5m
- **Kênh thông báo:** Slack (`#alerts-monitoring-l3a`)
- **SLI/SLO liên quan:** Primary SLO `fast_successful_requests` (Target: 99.5% requests <= 3000ms).
- **Điều kiện và thời gian duy trì:** P95 Latency > 3000ms kéo dài liên tục trên 5 phút.
- **Ảnh hưởng tới người dùng:** Người dùng trải nghiệm phản hồi chậm trễ, thời gian chờ câu trả lời từ chatbot tăng cao, nguy cơ timeout trên giao diện UI/Client.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở Panel 1 (Latency) trên Dashboard để kiểm tra TTFT (Time To First Token) và độ trễ P95/P99 bắt đầu tăng từ thời điểm nào.
  2. Tra cứu `data/logs.jsonl` tìm các request có `latency_ms > 3000`, trích xuất `correlation_id` tương ứng.
  3. Mở Langfuse trace theo `correlation_id` đó để xem waterfall: xác định độ trễ bắt nguồn từ span `retrieval` (RAG vector search) hay `llm-generation` (LLM inference).
- **Mitigation tạm thời:**
  - Nếu span `retrieval` chậm: Bật incident mitigation hoặc kích hoạt cache cho vector store.
  - Nếu span `llm-generation` chậm: Hạ số lượng tài liệu ngữ cảnh (`doc_count`), chuyển tải sang model dự phòng (fallback model), hoặc áp dụng rate limit tạm thời đối với traffic lớn.
- **Owner:** `llmops-oncall`

---

## Alert 2: High Request Error Rate

- **Tên:** HighRequestErrorRate
- **Severity:** critical
- **Duration:** 3m
- **Kênh thông báo:** Slack (`#alerts-monitoring-l3a`)
- **SLI/SLO liên quan:** Guardrail Error Rate <= 2% và Primary SLO `fast_successful_requests`.
- **Điều kiện và thời gian duy trì:** Tỷ lệ lỗi `error_rate_pct > 2%` kéo dài liên tục trên 3 phút.
- **Ảnh hưởng tới người dùng:** Người dùng nhận lỗi HTTP 500 (`Internal Server Error`), không nhận được câu trả lời từ trợ lý ảo, dịch vụ gián đoạn diện rộng.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở Panel 3 (Errors) trên Dashboard để xác định loại lỗi phổ biến nhất (`error_type`, ví dụ: `RuntimeError`, `RateLimitError`, `TimeoutError`).
  2. Lọc file `data/logs.jsonl` với sự kiện `event == "request_failed"` để đọc thông tin chi tiết `payload.detail` và `correlation_id`.
  3. Truy cập Langfuse tra cứu trace tương ứng để xem span nào phát sinh exception và stack trace chi tiết.
- **Mitigation tạm thời:**
  - Kiểm tra xem có incident giả lập nào đang bật không (`GET /health` kiểm tra trường `incidents`), nếu có sự cố tool fail hoặc inject lỗi thì tắt qua `POST /incidents/{name}/disable`.
  - Khởi động lại service API hoặc bật chế độ safe-mode (trả về fallback template answer thay vì throw 500).
- **Owner:** `llmops-oncall`

---

## Alert 3: Low Retrieval Success Rate

- **Tên:** LowRetrievalSuccessRate
- **Severity:** warning
- **Duration:** 5m
- **Kênh thông báo:** Slack (`#alerts-monitoring-l3a`)
- **SLI/SLO liên quan:** Guardrail Retrieval Success Rate >= 90% và Panel Quality Proxy >= 0.75.
- **Điều kiện và thời gian duy trì:** Tỷ lệ retrieval thành công `retrieval_success_rate_pct < 90%` trong vòng 5 phút.
- **Ảnh hưởng tới người dùng:** Agent không lấy được tài liệu ngữ cảnh liên quan, dẫn đến câu trả lời bị cụt, chất lượng câu trả lời suy giảm (Quality Score giảm dưới 0.75), hoặc phản hồi không chính xác (hallucination).
- **Ba bước kiểm tra đầu tiên:**
  1. Kiểm tra log `event == "request_failed"` hoặc `response_sent` có `tool_name == "retrieval"` và `tool_success == false`.
  2. Mở trace trên Langfuse, quan sát observation `retrieval` xem tài liệu trả về có rỗng (`doc_count == 0`) hoặc gặp lỗi kết nối tới cơ sở dữ liệu tri thức không.
  3. Kiểm tra trạng thái endpoint `/health` xem cờ `tool_fail` có đang bị kích hoạt hay không.
- **Mitigation tạm thời:**
  - Nếu do sự cố inject incident: tắt cờ `tool_fail` thông qua `POST /incidents/tool_fail/disable`.
  - Nếu do nguồn RAG vector database: chuyển hướng sang index dự phòng hoặc chuyển agent sang chế độ direct answer (chỉ dùng knowledge của LLM kèm cảnh báo độ tin cậy).
- **Owner:** `rag-team`
