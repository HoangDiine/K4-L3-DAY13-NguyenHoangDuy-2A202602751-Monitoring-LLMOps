# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Hoàng Duy
- **MSSV:** 2A202602751
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/HoangDiine/K4-L3-DAY13-NguyenHoangDuy-2A202602751-Monitoring-LLMOps.git
- **Commit SHA cuối:** 94dd3897b3e0c86bffd87cbc83219beeac8abb9a
- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602751`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.


| Evidence            | Đường dẫn                         |
| ------------------- | ------------------------------------- |
| Pytest cuối        | `evidence/01-pytest.png`              |
| Log validator       | `evidence/02-log-validator.png`       |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log      | `evidence/04-structured-log.txt`      |
| PII redaction       | `evidence/05-pii-redaction.txt`       |
| Trace list          | `evidence/06-trace-list.png`          |
| Trace waterfall     | `evidence/07-trace-waterfall.png`     |
| Trace metadata      | `evidence/08-trace-metadata.png`      |
| Prompt versions     | `evidence/09-prompt-versions.png`     |
| Prompt rollback     | `evidence/10-prompt-rollback_v1.png`, `evidence/10-prompt-rollback_v2.png` |
| Dashboard runtime   | `evidence/11-dashboard-overview.png`  |
| Incident metric     | `evidence/12-incident-metric.png`     |
| Incident log        | `evidence/13-incident-log.txt`        |
| Incident trace      | `evidence/14-incident-trace.png`      |

## 3. Kết quả kỹ thuật


| Nội dung               | Baseline | Kết quả cuối | Nhận xét |
| ----------------------- | -------- | --------------- | ---------- |
| `validate_logs.py`      | 30/100 | 100/100 | Đạt điểm tuyệt đối 100/100; đầy đủ các trường bắt buộc (`ts`, `level`, `service`, `event`, `correlation_id`), context enrichment đầy đủ (`user_id_hash`, `session_id`, `feature`, `model`, `env`), và không có PII leak nào. |
| `validate_dashboard.py` | 6/6 panel hợp lệ | 6/6 panel hợp lệ | Contract YAML chuẩn schema 6 panel theo quy định (latency, traffic, errors, cost, tokens, quality). |
| `pytest`                | 22 passed | 27 passed | Toàn bộ 27/27 unit & integration tests pass (thêm tests cho PII regex, correlation ID propagation, child observations). |
| Số traces hợp lệ     | 0 | 15+ | 15+ traces với đầy đủ span tree 3 tầng: root (`lab-agent-run`), retriever (`retrieval`), generation (`llm-generation`) kèm usage/cost. |
| Số PII leak            | 0 | 0 | 0 rò rỉ, toàn bộ PII (email, phone, cccd, thẻ) được khử bằng `[REDACTED_*]` trước khi serialize/ghi log file. |
| Latency P95 / TTFT P95  | 1269.0 ms / 57.0 ms | 165.7 ms / 50.0 ms | Đo lường thực tế từ đợt chạy load test sau khi hoàn thiện child observations. |
| Retrieval success rate  | 100% | 100% | Hệ thống hoạt động bình thường, retrieval thành công. |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  - Trong `CorrelationIdMiddleware` (`app/middleware.py`), đầu tiên gọi `clear_contextvars()` để tránh rò rỉ context giữa các request.
  - Kiểm tra header `x-request-id` từ request đến; nếu có thì tái sử dụng, nếu không có hoặc rỗng thì sinh mới theo định dạng `req-<8-hex>` thông qua `f"req-{uuid.uuid4().hex[:8]}"`.
  - Gắn vào structlog contextvars thông qua `bind_contextvars(correlation_id=correlation_id)` và lưu vào `request.state.correlation_id`.
  - Đo thời gian xử lý và trả về trong response headers: `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:**
  - Các trường bắt buộc: `ts` (ISO UTC timestamp), `level` (info, warning, error), `service` (`api`), `event` (`request_received`, `response_sent`, `request_failed`).
  - Tracing & định danh request: `correlation_id`.
  - Context enrichment (được bind tại endpoint `/chat` trước khi log `request_received`): `user_id_hash` (băm SHA-256 lấy 12 ký tự đầu qua `hash_user_id`), `session_id`, `feature`, `model` (`agent.model`), `env` (`os.getenv("APP_ENV", "dev")`).
  - Metrics vận hành (trong `response_sent`): `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, và `payload` (`message_preview`, `answer_preview`).
- **Cách bảo đảm PII được scrub trước khi ghi:**
  - Định nghĩa các regex pattern cho PII trong `app/pii.py`: `email` (`[\w\.\+-]+@[\w\.-]+\.\w+`), `phone_vn` (`(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)`), `cccd` (`(?<!\d)\d{12}(?!\d)`), `credit_card` (`\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b`).
  - Hàm `scrub_text` thay thế các thông tin nhạy cảm thành nhãn dạng `[REDACTED_<TYPE>]`.
  - Đăng ký processor `scrub_event` trong `app/logging_config.py` ở vị trí đứng TRƯỚC `JsonlFileProcessor()` và `JSONRenderer()`. Mọi trường dạng dict, list, string trong event dict đều được khử PII đệ quy trước khi render ra JSON hoặc ghi vào file `data/logs.jsonl`.
- **Cách kiểm chứng kết quả:**
  - Chạy `python scripts/validate_logs.py`: đạt điểm tuyệt đối 100/100 (0 bản ghi thiếu required field, 0 bản ghi thiếu enrichment, 10/10 unique correlation IDs, 0 PII leak).
  - Chạy `python -m pytest -q`: toàn bộ 27/27 tests passed.
  - Kiểm tra trực tiếp file `data/logs.jsonl` và response headers (`x-request-id`, `x-response-time-ms`) của API `/chat`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  - Project Langfuse: `day13-k4-l3a-2A202602751` (tương ứng với MSSV 2A202602751).
  - Sử dụng cặp key riêng `LANGFUSE_PUBLIC_KEY` (`pk-lf-0b2705ed...`) và `LANGFUSE_SECRET_KEY` trong `.env`.
  - Mọi trace đều gắn tag `tags=["lab", feature, self.model]`, `environment="dev"`, `session_id` và `user_id` băm SHA-256 (12 ký tự đầu).
- **Cấu trúc root/retrieval/generation observations:**
  - Observation gốc: `lab-agent-run` (type `AGENT`), đóng vai trò root span bao bọc toàn bộ chu kỳ xử lý request của agent.
  - Observation con 1: `retrieval` (type `RETRIEVER`), đo lường quá trình RAG truy xuất tài liệu liên quan, input chứa query đã khử PII (`summarize_text`), output chứa `doc_count`.
  - Observation con 2: `llm-generation` (type `GENERATION`), đo lường cuộc gọi LLM generation, liên kết managed prompt, input/output đã scrub PII, kèm `usage_details` (`tokens_in`, `tokens_out`, `total`) và `cost_details` (`cost_usd`).
- **Cách nối trace với log:**
  - `correlation_id` (định dạng `req-<8-hex>`) được sinh từ middleware và đính kèm vào trace metadata (`metadata={"correlation_id": correlation_id, ...}`).
  - Trong log file `data/logs.jsonl`, các sự kiện `request_received` và `response_sent` đều lưu cùng trường `correlation_id`.
  - Khi điều tra một log bất thường, chỉ cần trích xuất `correlation_id` và tìm kiếm trên Langfuse để mở trace waterfall tương ứng.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (Labels: `['baseline', 'production']`)
- **Version/label candidate:** Version 2 (Labels: `['candidate']`)
- **Trace ID của mỗi version:**
  - Baseline v1: `caf5b8d27a96f0b3c3240f962a79187b` (Correlation ID: `req-prompt-v1-baseline`)
  - Candidate v2: `33320efc53037e8d701591dbf5ddd15e` (Correlation ID: `req-prompt-v2-candidate`)
  - Promoted v2: `9d956e1b1875fa83073ea7988d1484c9` (Correlation ID: `req-prompt-v2-promoted`)
  - Rollback v1: `ed207de6e5ddb73e5ca1bff80b77ac82` (Correlation ID: `req-prompt-v1-rollback`)
- **Cách promote và rollback `production`:**
  - Promote: Sử dụng API `client.update_prompt(name='day13-chat', version=2, new_labels=['candidate', 'production'])` để chuyển label `production` sang Version 2.
  - Rollback: Khi cần quay về bản cũ, gọi `client.update_prompt(name='day13-chat', version=1, new_labels=['baseline', 'production'])`. Nhãn `production` chuyển về Version 1 ngay lập tức mà không cần sửa code hay khởi động lại app.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  - Panel 1 (`latency`): Latency percentiles P50/P95/P99 và TTFT P95 từ event `response_sent`, đơn vị ms, threshold P95 <= 3000ms.
  - Panel 2 (`traffic`): Request traffic rate per minute và count từ event `request_received`, đơn vị req/min, threshold rate >= 1.
  - Panel 3 (`errors`): Error rate % (`request_failed / request_received * 100`), phân loại `error_type`, và `tool_success_rate_pct`, threshold error_rate <= 2%.
  - Panel 4 (`cost`): Chi phí tích lũy theo phút và tổng chi phí (`sum(cost_usd)`), đơn vị USD, threshold total <= $2.5.
  - Panel 5 (`tokens`): Tổng token vào/ra (`sum(tokens_in)`, `sum(tokens_out)`), đơn vị tokens, threshold <= 50,000.
  - Panel 6 (`quality`): Điểm chất lượng trung bình (`mean(quality_score)`), thang điểm 0..1, threshold mean >= 0.75.
- **SLO và lý do chọn:**
  - Tên SLO: `fast_successful_requests` với chu kỳ đánh giá 28 ngày (`window: 28d`).
  - Định nghĩa SLI: $\text{SLI} = \frac{\text{Số request response\_sent có latency\_ms} \le 3000}{\text{Tổng số request\_received nhận vào}} \times 100\%$.
  - Target: 99.5%.
  - Lý do chọn: Baseline thực tế cho thấy P95 trễ ổn định ở mức ~165-486ms (và ~1269ms lúc khởi động ban đầu). Ngưỡng 3000ms là giới hạn phù hợp để đảm bảo tương tác mượt mà cho người dùng chatbot, vừa đủ khoảng dung sai cho các đợt tải cao đột biến mà không gây báo động giả.
- **Cách tính error budget:**
  - $\text{Error Budget} = 100\% - 99.5\% = 0.5\%$.
  - Với lưu lượng giả định 1,000,000 request/tháng (28 ngày), ngân sách lỗi cho phép tối đa $0.5\% \times 1,000,000 = 5,000$ request bị lỗi HTTP 500 hoặc vượt quá ngưỡng độ trễ 3000ms trước khi tiêu cạn ngân sách lỗi.
- **Ba alert và runbook tương ứng:**
  - Alert 1: `HighResponseLatencyP95` (Warning, Duration: 5m, Condition: P95 latency > 3000ms, Kênh Slack, Runbook: `docs/alerts.md#alert-1-high-response-latency`).
  - Alert 2: `HighRequestErrorRate` (Critical, Duration: 3m, Condition: error_rate_pct > 2%, Kênh Slack, Runbook: `docs/alerts.md#alert-2-high-request-error-rate`).
  - Alert 3: `LowRetrievalSuccessRate` (Warning, Duration: 5m, Condition: retrieval_success_rate_pct < 90%, Kênh Slack, Runbook: `docs/alerts.md#alert-3-low-retrieval-success-rate`).

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** `2026-09-29T10:19:04Z` – `2026-09-29T10:19:24Z` (UTC) (tương ứng 17:19:04 – 17:19:24 GMT+7).
- **Triệu chứng từ metrics:** Panel 1 (`latency`) ghi nhận độ trễ P95 tăng vọt từ mức baseline ~152ms lên đỉnh điểm **3,769ms** (trung bình toàn batch đạt 2,876ms), vượt xa ngưỡng quy định trong challenge (`latency_threshold_ms: 2000ms`) và vi phạm SLO (`fast_successful_requests: <= 3000ms`). TTFT không đổi ở mức ~50ms, cho thấy backend nhận request bình thường nhưng xử lý nội bộ bị nghẽn.
- **Log line và correlation ID liên quan:**
  - `correlation_id`: `req-8b6e3d84`
  - Log line trích xuất từ `data/logs.jsonl`:
    ```json
    {"service": "api", "latency_ms": 3769, "ttft_ms": 50, "tokens_in": 35, "tokens_out": 178, "cost_usd": 0.002775, "quality_score": 0.8, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "correlation_id": "req-8b6e3d84", "session_id": "k4-l3a-challenge-s01", "env": "dev", "feature": "monitoring", "model": "claude-sonnet-4-5", "user_id_hash": "dde2e75b20cf", "level": "info", "ts": "2026-09-29T10:19:10.648534Z"}
    ```
- **Trace ID và span gây ảnh hưởng:**
  - Trace ID: `594ed6a499a5eaa2aff62539f44dc523` (liên kết với `correlation_id: req-8b6e3d84`).
  - Span gây ảnh hưởng: Child observation `retrieval` (RETRIEVER) có thời gian xử lý kéo dài bất thường tới **2.500s** (2500ms), chiếm hơn 60% tổng thời lượng request (4.850s). Trong khi đó, child observation `llm-generation` chỉ mất **0.151s** (151ms), khẳng định phần inference LLM hoạt động bình thường.
- **Root cause:** Module truy xuất tri thức RAG (`app/mock_rag.py`) gặp sự cố chậm trễ do incident `rag_slow` bị kích hoạt, làm hàm `retrieve` bị sleep 2.5 giây (`time.sleep(2.5)`). Trong môi trường thực tế, đây tương ứng với sự cố quá tải I/O mạng hoặc truy vấn vector database chưa được đánh chỉ mục tối ưu.
- **Fix action:**
  - Tắt cờ sự cố ngay lập tức thông qua endpoint quản trị: `POST /incidents/rag_slow/disable` (chạy script `python scripts/inject_incident.py --disable`).
  - Hệ thống khôi phục trạng thái hoạt động bình thường, kiểm tra lại độ trễ `latency_ms` lập tức trở về mức baseline (~152ms).
- **Preventive measure:**
  - Thiết lập timeout nghiêm ngặt cho truy vấn retrieval tới Vector Database (ví dụ: hard timeout 1000ms), kèm cơ chế fallback trả về kết quả từ in-memory cache hoặc trả về câu trả lời tổng quát từ LLM kèm cảnh báo.
  - Kích hoạt alert `HighResponseLatencyP95` (với duration 5 phút) để cảnh báo sớm cho đội on-call khi P95 > 3000ms trước khi tiêu cạn Error Budget của SLO.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  - Đặt processor khử PII `scrub_event` đứng TRƯỚC file writer và JSON renderer trong cấu hình pipeline của `structlog`. Quyết định này giúp triệt tiêu hoàn toàn nguy cơ rò rỉ dữ liệu nhạy cảm (PII) ngay từ gốc trước khi dữ liệu được ghi vào file hay gửi ra bất kỳ output destination nào.
- **Một lỗi/blocker đã gặp:**
  - Khi chạy pytest trên môi trường Windows, `pytest` gặp lỗi phân quyền truy cập tại thư mục tạm thời `AppData/Local/Temp/pytest-of-...`, dẫn đến fail test hàng loạt.
- **Cách tìm nguyên nhân và xử lý:**
  - Đọc kỹ stack trace xác định lỗi `PermissionError` trên Windows; giải quyết bằng cách cấu hình file `pytest.ini` với cờ `addopts = --basetemp=.pytest_cache/tmp` để trỏ toàn bộ thư mục tạm thời về bên trong workspace của dự án.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - **Metrics** (Phát hiện): Dashboard và alert phát hiện triệu chứng bất thường diện rộng (P95 latency tăng vọt lên 3.7s, vượt threshold 2000ms).
  - **Logs** (Khu trú): Tra cứu file `data/logs.jsonl` trong khoảng thời gian xảy ra sự cố, lọc các request có độ trễ cao và trích xuất mã định danh `correlation_id: req-8b6e3d84`.
  - **Traces** (Định vị nguyên nhân gốc): Dùng `correlation_id` tra cứu Trace waterfall trên Langfuse, quan sát chi tiết từng span trong cây thực thi và xác định span `retrieval` chiếm 2.50s trong khi `llm-generation` chỉ 0.15s, định vị chính xác điểm nghẽn nằm ở khâu RAG retrieval.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - Quản lý prompt qua version và label cho phép triển khai prompt mới an toàn và rollback tức thì về bản stable mà không cần sửa code hay redeploy service. Theo dõi token và cost giúp ngăn chặn hiện tượng chi phí tăng vọt. SLO và Error Budget giúp cân bằng giữa tốc độ cải tiến tính năng và độ ổn định của hệ thống.
- **Điều quan trọng nhất đã học:**
  - Nắm vững kiến trúc Observability 3 trụ cột (Metrics - Logs - Traces) trong thực tế vận hành hệ thống AI/LLM, hiểu sâu về bảo vệ quyền riêng tư (PII scrubbing) và quản lý vòng đời prompt có thể rollback an toàn.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  - Hệ thống hiện tại đang sử dụng các module mock cho fake LLM và fake retriever để phục vụ bài lab; hướng phát triển tiếp theo là kết nối với các provider LLM thương mại (OpenAI, Anthropic) và cơ sở dữ liệu vector thực tế.

## 9. Checklist trước khi nộp

- [x]  Kết quả và evidence thuộc commit SHA cuối.
- [x]  Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x]  Incident evidence nối đúng metric → log → trace.
- [x]  Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x]  Repository chạy lại được theo README.
- [x]  Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ]  URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
