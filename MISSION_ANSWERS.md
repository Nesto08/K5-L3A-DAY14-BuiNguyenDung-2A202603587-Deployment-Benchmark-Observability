# MISSION ANSWERS — DAY 14

## Part 1 — Localhost vs Production

### Exercise 1.1 — Anti-patterns

Các vấn đề phát hiện trong `develop/app.py`:

1. API key được hardcode trong source code.
2. Database URL chứa thông tin đăng nhập trực tiếp.
3. Không quản lý cấu hình bằng environment variables.
4. Sử dụng `print()` thay cho structured logging.
5. Ghi API key vào log.
6. Không có health check và readiness check.
7. Port cố định tại 8000.
8. Chỉ bind vào localhost.
9. Luôn bật reload.
10. Không có lifecycle cleanup riêng.

### Exercise 1.2 — Basic version

Chạy thành công trên Ubuntu WSL2 với mock LLM.

| Endpoint | HTTP status |
|---|---|
| GET / | 200 |
| POST /ask?question=Hello | 200 |
| GET /health | 404 |
| GET /ready | 404 |

**Nhận xét:** Agent hoạt động trên localhost nhưng chưa phù hợp để triển khai production do thiếu cơ chế giám sát, quản lý cấu hình và bảo mật secret.

### Exercise 1.3 — Advanced version

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---|---|---|---|
| Config | Hardcode | Environment variables | Linh hoạt khi triển khai, tránh lộ secret |
| Health check | Không có | /health, /ready | Giám sát trạng thái và điều phối traffic |
| Logging | print() | Structured JSON logging | Hỗ trợ giám sát và phân tích lỗi |
| Shutdown | Không có cleanup riêng | Graceful shutdown qua lifespan | Dừng ứng dụng an toàn |
| Host | localhost | 0.0.0.0 | Hỗ trợ truy cập từ bên ngoài container |
| Port | Cố định | Đọc từ config | Tương thích cloud platform |
| Reload | Luôn bật | Theo cấu hình debug | Giảm overhead khi chạy production |

**Kết quả kiểm thử thực tế:**

| Endpoint | HTTP status |
|---|---|
| GET / | 200 |
| GET /health | 200 |
| GET /ready | 200 |
| POST /ask | 200 |
| GET /metrics | 200 |
| POST /ask với JSON rỗng | 422 |

- API tests: 6/6 PASS.
- Agent version: 1.0.0.
- Uptime tại thời điểm kiểm tra health: 29.6 giây.
- Readiness: true.
- LLM: Mock LLM.
- Environment: development.

**Graceful shutdown:** Uvicorn ghi nhận Application shutdown complete và Finished server process. Tuy nhiên, sau khi nhấn Ctrl+C vẫn xuất hiện traceback CancelledError và KeyboardInterrupt trên Python 3.14.4. Chưa xác định nguyên nhân chính xác.

**Kết luận:** Advanced version cải thiện khả năng cấu hình, giám sát và quản lý vòng đời ứng dụng so với Basic version.

## AI Log

- CP1: Sử dụng ChatGPT hỗ trợ phân tích anti-patterns, giải thích code, cung cấp lệnh kiểm thử và tổng hợp kết quả.
- Tự chạy kiểm thử trên Ubuntu WSL2, đối chiếu HTTP status và log thực tế.

## Part 2 — Docker Containerization

### Exercise 2.1 — Dockerfile cơ bản

1. Base image: `python:3.11`.
2. Working directory: `/app`.
3. COPY `requirements.txt` trước để tận dụng Docker layer caching, tránh cài lại dependencies khi chỉ thay đổi source code.
4. CMD cung cấp lệnh hoặc đối số mặc định khi container khởi động. ENTRYPOINT xác định chương trình chính của container.

### Exercise 2.2 — Build và chạy Develop Image

- Image: `agent-develop:latest`.
- Build time: 37.1 giây.
- Image size: 1667.78 MB.
- GET /health: HTTP 200.
- POST /ask: HTTP 200.
- Health status: ok.
- Container: true.
- Uptime khi kiểm thử: 12.7 giây.

Kết quả: PASS.

### Exercise 2.3 — Multi-stage Build

Dockerfile production sử dụng hai stage:

- Builder: cài dependencies và build tools trên `python:3.11-slim`.
- Runtime: chỉ copy dependencies và source code cần thiết, sử dụng non-root user và healthcheck.

| Tiêu chí | Develop | Production |
|---|---|---|
| Base image | python:3.11 | python:3.11-slim |
| Build stages | 1 | 2 |
| User | root | appuser |
| Docker Healthcheck | Không | Có |
| Image size | 1667.78 MB | 239.82 MB |
| Image size (bytes) | 1667780015 | 239815252 |

- Dung lượng giảm: 1427.96 MB.
- Tỷ lệ giảm: 85.62%.
- Mục tiêu production image dưới 500 MB: ĐẠT.

**Kiểm thử production container:**

- GET /health: HTTP 200.
- Container user: appuser.
- Healthcheck: healthy.
- Uvicorn: 2 workers.
- Structured logging: hoạt động.
- Agent version: 2.0.0.

Kết quả: PASS.

### Exercise 2.4 — Docker Compose

**Sơ đồ kiến trúc:**

```mermaid
flowchart TD
    Client["Client"] -->|"HTTP :80"| Nginx["Nginx - Reverse Proxy"]
    subgraph Network["Internal Bridge Network"]
        Nginx -->|"Port 8000"| Agent["FastAPI Agent - 2 workers"]
        Agent -.->|"Configured dependency"| Redis["Redis :6379"]
        Agent -.->|"Configured dependency"| Qdrant["Qdrant :6333"]
        Redis --- RV["redis_data"]
        Qdrant --- QV["qdrant_data"]
    end
```

**Kết quả khởi động:**

| Service | Status |
|---|---|
| Agent | Healthy |
| Redis | Healthy |
| Qdrant | Healthy |
| Nginx | Running |

**Kiểm thử API qua Nginx:**

| Endpoint | HTTP status |
|---|---|
| GET / | 200 |
| GET /health | 200 |
| GET /ready | 200 |
| POST /ask | 200 |
| POST /ask với JSON rỗng | 422 |

- API tests: 5/5 PASS.
- Environment: staging.
- Redis: PONG.
- Qdrant TCP connectivity: OK.
- Reverse proxy: Server nginx.
- Security headers trên response 200: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection.

**Rate Limiting:**

- Cấu hình: 10 requests/giây/IP, burst 20.
- Tổng request: 100.
- Concurrency tối đa: 30.
- HTTP 200: 21.
- HTTP 429: 79.
- HTTP 5xx: 0.
- Các service vẫn hoạt động sau kiểm thử.

Kết quả: PASS.

**Hạn chế của cấu hình mẫu:**

- Một Agent container chạy hai workers, chưa triển khai hai replicas.
- Redis và Qdrant đã khởi động nhưng chưa được tích hợp vào logic xử lý request.
- Port 443 được khai báo nhưng chưa cấu hình TLS.
- Security headers chưa áp dụng cho mọi HTTP status.
- Docker Compose cảnh báo thuộc tính version đã lỗi thời.

**Cleanup:** Docker Compose down thành công, xóa bốn container và một network. Không xóa persistent volumes.

**Kết luận:** CP2 hoàn thành. Multi-stage build kết hợp slim base image giảm 85.62% kích thước image. Docker Compose khởi động thành công bốn service, reverse proxy và rate limiting hoạt động đúng trong kiểm thử local.

### AI Log — CP2

- Sử dụng ChatGPT hỗ trợ phân tích Dockerfile, giải thích multi-stage build, Docker Compose và rate limiting.
- AI hỗ trợ xử lý lỗi HTTP 429 khi tải base image từ Docker Hub.
- Tự thực hiện build, chạy container, kiểm thử API và thu thập số liệu thực tế.

## Part 4 — API Gateway & Security (CP3)

### 4.1. Basic — API Key Authentication

Chạy ứng dụng Basic và kiểm thử xác thực thông qua header `X-API-Key`.

| Trường hợp | HTTP status | Kết quả |
|---|---|---|
| API Key hợp lệ | 200 | PASS |
| Không có API Key | 401 | PASS |
| API Key không hợp lệ | 403 | PASS |

### 4.2. Advanced — JWT Authentication

Cấu hình:

- JWT Algorithm: HS256.
- Token expiration: 60 phút.
- Student: role user, 10 request/phút.
- Teacher: role admin, 100 request/phút.

| Trường hợp | Kết quả thực tế |
|---|---|
| Health Check | 200 |
| Đăng nhập sai mật khẩu | 401 |
| Đăng nhập đúng | Nhận JWT dài 168 ký tự |
| JWT hợp lệ | 200 |
| Thiếu JWT | 401 |
| JWT không hợp lệ | 403 |
| Student truy cập `/admin/stats` | 403 |
| Teacher truy cập `/admin/stats` | 200 |

Kết quả: PASS 8/8.

### 4.3. Rate Limiting

Sử dụng Sliding Window với giới hạn 10 request/60 giây đối với Student.

Gửi liên tiếp 20 request:

| Chỉ số | Kết quả |
|---|---:|
| Tổng request | 20 |
| HTTP 200 | 10 |
| HTTP 429 | 10 |
| Tỷ lệ request bị chặn | 50% |

Request 1–10 được xử lý thành công, request 11–20 bị chặn. Rate Limiter hoạt động đúng với cấu hình.

### 4.4. Input Validation

Pydantic kiểm tra trường `question` với độ dài từ 1 đến 1000 ký tự.

| Trường hợp | HTTP status | Kết quả |
|---|---|---|
| Thiếu question | 422 | PASS |
| Question rỗng | 422 | PASS |
| Question dài 1001 ký tự | 422 | PASS |
| Question hợp lệ | 200 | PASS |

### 4.5. Cost Guard

Cấu hình ngân sách:

- Per-user daily budget: $1.
- Global daily budget: $10.
- Warning threshold: 80%.

Kiểm thử độc lập class `CostGuard` bằng dữ liệu token giả lập:

| Test case | Kết quả thực tế |
|---|---|
| Normal Budget | Request allowed |
| Usage Tracking | $0.00075 |
| Budget Warning | WARNING tại 84% |
| User Budget Exceeded | Exception 402 tại $1.20 |
| Global Budget Exceeded | Exception 503 tại khoảng $14.0407 |

Kết quả: PASS 5/5.

Thống kê thực tế từ endpoint `/me/usage` của Student:

| Metric | Giá trị |
|---|---:|
| Requests | 11 |
| Input tokens | 66 |
| Output tokens | 330 |
| Cost USD | 0.000208 |
| Budget USD | 1.0 |
| Remaining budget USD | 0.999792 |

Toàn bộ token và chi phí được giả lập, không sử dụng LLM API thật.

### 4.6. Security Headers

Các header quan sát được trong HTTP response:

- X-Content-Type-Options: nosniff.
- X-Frame-Options: DENY.
- X-XSS-Protection: 1; mode=block.
- Referrer-Policy: strict-origin-when-cross-origin.

### 4.7. Câu hỏi thảo luận

**1. Khi nào nên dùng API Key vs JWT vs OAuth2?**

- API Key: phù hợp với giao tiếp service-to-service hoặc API đơn giản.
- JWT: phù hợp với hệ thống có đăng nhập, phân quyền và token hết hạn.
- OAuth2: phù hợp khi cần cấp quyền truy cập cho ứng dụng bên thứ ba mà không chia sẻ mật khẩu người dùng.

**2. Rate limit nên đặt bao nhiêu request/phút cho một AI Agent?**

Phụ thuộc vào chi phí model, độ phức tạp của request, tài nguyên hệ thống và nhu cầu người dùng. Có thể bắt đầu với 10 request/phút cho user thông thường và 100 request/phút cho admin như trong lab, sau đó điều chỉnh dựa trên benchmark và ngân sách.

**3. Nếu API Key bị lộ, phát hiện và xử lý như thế nào?**

- Phát hiện thông qua audit log, bất thường về request, chi phí và secret scanning.
- Thu hồi API Key bị lộ ngay lập tức.
- Tạo key mới và cập nhật secret trên hệ thống.
- Kiểm tra lịch sử sử dụng để xác định phạm vi ảnh hưởng.
- Sử dụng Secret Manager, giới hạn quyền và ngân sách để giảm rủi ro.

### 4.8. Hạn chế và đề xuất cải thiện

- JWT secret mặc định và tài khoản demo được hardcode.
- Rate Limiter và Cost Guard sử dụng in-memory, cần Redis hoặc database khi triển khai nhiều instance.
- Header `server: uvicorn` vẫn xuất hiện trong HTTP response.
- Trường `budget_remaining_usd` tại `/ask` trả về chi phí đã sử dụng thay vì ngân sách còn lại.
- Global budget chưa có cơ chế reset theo ngày.
- Cost Guard chưa dự trù chi phí của request tiếp theo trước khi gọi LLM.
- Chưa kiểm thử JWT hết hạn, header Retry-After và HTTP 402/503 end-to-end.

### 4.9. AI Usage Log

- Công cụ: ChatGPT.
- Mục đích: hỗ trợ đọc hiểu source code, xây dựng lệnh kiểm thử API Key, JWT, RBAC, Rate Limiting, Input Validation và Cost Guard.
- Kiểm chứng: trực tiếp chạy ứng dụng và các lệnh kiểm thử trên WSL Ubuntu, đối chiếu HTTP response và terminal log.
- Kết quả: hoàn thành các kiểm thử chính của Section 4 và xác định một số hạn chế của ứng dụng mẫu.


## Part 5 — Scaling & Reliability (CP4)

### 5.1. Health Check & Graceful Shutdown

Chạy ứng dụng Develop trên WSL Ubuntu, sử dụng FastAPI 0.115.0, Uvicorn 0.30.0 và psutil 6.0.0.

| Kiểm thử | Kết quả |
|---|---|
| GET /health | HTTP 200, status: ok |
| GET /ready | HTTP 200, ready: true |
| POST /ask | HTTP 200, mock response |
| Uptime tại Health Check | 273.4 giây |
| Memory usage | 16.0% |
| Server PID | 6489 |

**Graceful Shutdown:**

- Gửi 2 request song song.
- Gửi tín hiệu SIGTERM sau 0.5 giây.
- Request 1: HTTP 200.
- Request 2: HTTP 200.
- Số request hoàn thành: 2/2.
- Số request bị mất trong lần thử: 0.
- Process PID 6489 đã dừng và port 8000 được giải phóng.

Kết quả phù hợp với mục tiêu Graceful Shutdown. Tuy nhiên, chưa thu thập log shutdown và thời gian xử lý từng request để xác nhận cả hai request vẫn đang xử lý tại thời điểm nhận SIGTERM.

### 5.2. Stateless Agent + Redis + Nginx

Khởi chạy hệ thống:

```bash
docker compose up -d --build --scale agent=3
```

Docker build thành công trong 46.9 giây. Hệ thống gồm 3 Agent instances, 1 Redis và 1 Nginx.

Kiến trúc:

```mermaid
graph TD
    Client --> Nginx
    Nginx --> Agent1
    Nginx --> Agent2
    Nginx --> Agent3
    Agent1 <--> Redis
    Agent2 <--> Redis
    Agent3 <--> Redis
```

| Container | Instance ID | Trạng thái |
|---|---|---|
| Agent 1 | instance-dd2dbc | Healthy |
| Agent 2 | instance-dc40c9 | Healthy |
| Agent 3 | instance-5b7193 | Healthy |
| Redis | — | Healthy |
| Nginx | — | Running |

Cả 3 Agent instances đều kết nối Redis thành công. Redis trả về PONG. Hai endpoint /health và /ready thông qua Nginx đều trả HTTP 200.

### 5.3. Kiểm thử Stateless Session

Chạy:

```bash
python test_stateless.py
```

Session ID: `d150aa81-efda-4b0c-a2a7-7d4c3250087f`

| Request | Instance xử lý |
|---|---|
| 1 | instance-dc40c9 |
| 2 | instance-5b7193 |
| 3 | instance-dd2dbc |
| 4 | instance-dc40c9 |
| 5 | instance-5b7193 |

Kết quả:

- Tổng request thành công: 5/5.
- Số instance tham gia: 3/3.
- Tổng messages: 10/10.
- User messages: 5.
- Assistant messages: 5.
- Không mất lịch sử hội thoại trong bài kiểm thử.

Kiểm tra trực tiếp Redis:

| Tiêu chí | Kết quả |
|---|---|
| Session key | Tồn tại |
| DBSIZE | 1 |
| TTL cấu hình | 3600 giây |
| TTL còn lại khi kiểm tra | 3319 giây |
| Total messages | 10 |
| User messages | 5 |
| Assistant messages | 5 |
| Assertion | PASS |

### 5.4. Kiểm thử Load Balancing

Gửi 12 request GET /health thông qua Nginx.

| Instance | Requests | Tỷ lệ |
|---|---:|---:|
| instance-dd2dbc | 4 | 33.33% |
| instance-dc40c9 | 4 | 33.33% |
| instance-5b7193 | 4 | 33.33% |
| Tổng | 12 | 100% |

Nginx phân phối request đồng đều giữa 3 instances trong bài kiểm thử.

### 5.5. So sánh Develop và Production

| Tiêu chí | Develop | Production |
|---|---|---|
| Instances | 1 | 3 |
| State | In-memory | Redis-backed session |
| Load Balancer | Không có | Nginx |
| Scaling | Single instance | Horizontal scaling |
| Session TTL | Không áp dụng | 3600 giây |
| Deployment | Python local | Docker Compose |

### 5.6. Hạn chế và đề xuất cải thiện

- Redis fallback sang in-memory có thể làm mất khả năng chia sẻ session giữa các instances.
- Thao tác đọc–sửa–ghi session chưa đảm bảo atomic khi có request đồng thời.
- Redis chưa được cấu hình persistent volume riêng.
- Trường turn có khả năng bị lệch một đơn vị.
- Mock LLM chưa sử dụng conversation history để tạo câu trả lời.
- Test script gốc chưa có assertion kiểm tra số lượng messages; đã bổ sung kiểm tra trực tiếp bằng Redis CLI và Python.
- Chưa kiểm thử tải lớn, concurrent session updates hoặc khả năng phục hồi khi Redis gặp sự cố.

### 5.7. Kết luận

Hoàn thành triển khai và kiểm thử Health Check, Readiness, Graceful Shutdown, Horizontal Scaling, Load Balancing và Stateless Session.

Ba Agent instances có thể xử lý cùng một phiên hội thoại với lịch sử được lưu tập trung trong Redis. Kết quả kiểm thử xác nhận đầy đủ 10 messages sau 5 requests tuần tự.

Đã chạy `docker compose down`, xóa 5 containers và 1 network. Không còn container đang chạy. Không thay đổi source code mẫu.

**CP4: PASS đối với các bài kiểm thử đã thực hiện.**

### AI Usage Log — CP4

- Công cụ: ChatGPT.
- Mục đích: Hỗ trợ đọc source code, giải thích Health Check, Graceful Shutdown, Stateless Design, Redis và Nginx Load Balancing.
- AI hỗ trợ: Đề xuất lệnh triển khai, kiểm thử SIGTERM, kiểm tra phân phối request, Redis TTL và assertion xác minh conversation history.
- Người thực hiện: Trực tiếp chạy các lệnh trên WSL Ubuntu, kiểm tra output và đối chiếu kết quả thực tế.
- Kết quả: Hoàn thành CP4 với 3 Agent instances, 5 chat requests thành công, 10 messages được lưu và 12 health checks phân phối đồng đều.
- Kiểm chứng: Số liệu lấy từ terminal thực tế, không sử dụng số liệu giả lập cho báo cáo.


## Part 6 — Final Project: Production AI Agent (CP5)

### 1. Mục tiêu

Hoàn thiện Production AI Agent từ bản khung, đáp ứng đủ 12 tiêu chí Production Readiness trong README.md.

### 2. Nội dung thực hiện

- Hoàn thiện cấu hình ứng dụng từ environment variables.
- Triển khai API Key Authentication.
- Xây dựng Redis Client, Health Check và Readiness.
- Triển khai Rate Limiting và Cost Guard sử dụng Redis.
- Bổ sung Structured Logging và Graceful Shutdown.
- Xây dựng Dockerfile multi-stage, non-root và HEALTHCHECK.
- Hoàn thiện Docker Compose, .dockerignore.
- Chuẩn bị cấu hình triển khai Railway và Render.
- Giữ nguyên Mock LLM và script chấm của giảng viên.

### 3. Kết quả kiểm thử

| Tiêu chí | Kết quả |
|---|---|
| Dockerfile | PASS — 238 MB, nhỏ hơn 500 MB |
| Docker Compose | PASS — Agent + Redis |
| .dockerignore | PASS |
| Health Check | PASS — HTTP 200 |
| Readiness | PASS — HTTP 503 khi Redis mất kết nối |
| API Key Authentication | PASS — HTTP 401 khi thiếu hoặc sai key |
| Rate Limiting | PASS — HTTP 429 sau 5 request thành công |
| Cost Guard | PASS — HTTP 402 tại request đầu tiên trong bài test ngân sách thấp |
| Environment Config | PASS |
| Structured Logging | PASS — 12 dòng JSON hợp lệ |
| Graceful Shutdown | PASS — exit code 0, Docker stop 0.6 giây |
| Public URL Ready | PASS — Railway và Render config |

### 4. Kiểm thử Stateless và Reliability

- Agent sử dụng 2 Uvicorn workers.
- Rate Limiting lưu trạng thái trong Redis.
- Sau khi restart agent, trạng thái giới hạn request vẫn được duy trì.
- Khi Redis mất kết nối, /health vẫn trả HTTP 200 và /ready trả HTTP 503.
- Khi nhận SIGTERM, request đang xử lý vẫn trả HTTP 200 và process thoát với exit code 0.

### 5. Kết quả grader

| Giai đoạn | Tiêu chí đạt | Checks passed |
|---|---:|---:|
| Baseline | 0/12 | 5/36 |
| Stage 1 | 2/12 | 14/35 |
| Stage 2 | 3/12 | 16/35 |
| Final | 12/12 | 43/43 |

Lệnh kiểm thử cuối cùng:

`python check_production_ready.py`

Kết quả:

**PASS 12/12 — PRODUCTION READY!**

### 6. Bằng chứng

- `evidence/cp5/baseline-static.txt`
- `evidence/cp5/baseline-runtime.txt`
- `evidence/cp5/stage1-runtime.txt`
- `evidence/cp5/stage2-runtime.txt`
- `evidence/cp5/final-grader.txt`

### 7. Hạn chế

- Sử dụng Mock LLM, chưa gọi LLM thực tế.
- Chi phí token là giá trị ước tính.
- Cost Guard chưa có cơ chế giữ trước ngân sách cho các request đồng thời.
- Đã chuẩn bị cấu hình cloud nhưng chưa triển khai Public URL.

### 8. AI Usage Log

- Công cụ: ChatGPT.
- Mục đích: hỗ trợ phân tích yêu cầu, hoàn thiện code, cấu hình Docker và kiểm thử.
- Người thực hiện trực tiếp cập nhật source code, chạy grader và kiểm tra kết quả.
- Kết quả cuối cùng: 12/12 tiêu chí, 43/43 checks passed.
- Toàn bộ số liệu được lấy từ kết quả kiểm thử thực tế.