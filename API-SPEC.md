# Task Flow API 명세

PRD.md의 요구사항을 API 계약으로 정리한다. 구현 순서는 PLAN.md(T05~T08)를 따른다.

## 공통
- 기본 주소: `http://127.0.0.1:8000` (개발), 모든 경로는 `/api`로 시작한다.
- 요청·응답 본문은 JSON(UTF-8)이다.
- 날짜는 `YYYY-MM-DD`, 일시는 ISO 8601 UTC 문자열(예: `2026-10-13T05:12:30Z`)이다.
- 오류 응답은 FastAPI 기본 형식 `{"detail": ...}`을 사용한다.

| 상태 코드 | 의미 |
|---|---|
| 200 | 조회·수정 성공 |
| 201 | 등록 성공 |
| 204 | 삭제 성공(본문 없음) |
| 404 | 해당 id의 할 일이 없음 |
| 422 | 입력값 검증 실패 |
| 503 | DB 연결 실패 또는 DB 처리 오류. 응답: `{"detail": "DB에 연결할 수 없거나 처리 중 오류가 발생했습니다."}` |

## Task 객체

| 필드 | 타입 | 규칙 | 기본값 |
|---|---|---|---|
| id | 정수 | 서버가 발급하는 고유 값. 수정·삭제는 id로 처리한다. | - |
| title | 문자열 | 앞뒤 공백 제거 후 1~100자 | 필수 |
| description | 문자열 | 최대 2000자 | `""` |
| status | 문자열 | `TODO`, `DOING`, `DONE` | `TODO` |
| priority | 문자열 | `HIGH`, `NORMAL`, `LOW` | `NORMAL` |
| due_date | 문자열 또는 null | 실제 존재하는 `YYYY-MM-DD` 날짜, 미지정은 null | `null` |
| created_at | 문자열 | 등록 시 서버가 기록하는 UTC 일시 | - |

```json
{
  "id": 1,
  "title": "보고서 작성",
  "description": "",
  "status": "TODO",
  "priority": "HIGH",
  "due_date": "2026-10-20",
  "created_at": "2026-10-13T05:12:30Z"
}
```

- 정의되지 않은 필드를 보내면 422로 거절한다.
- 지연 여부는 사용자의 로컬 날짜가 필요하므로 API가 아닌 화면에서 계산한다.

## 엔드포인트

### GET /api/health  (T05)
API 서버 상태를 확인한다.
- 응답 200: `{"status": "ok"}`

### GET /api/tasks  (T06, 필터는 T07)
할 일 목록을 등록 순서(id 오름차순)로 반환한다.

| 쿼리 | 설명 |
|---|---|
| q | 제목에 포함된 글자(대소문자 무시, 앞뒤 공백 제거). 비어 있으면 조건 없음 |
| status | `TODO`, `DOING`, `DONE` 중 하나 |
| priority | `HIGH`, `NORMAL`, `LOW` 중 하나 |

- 여러 조건은 AND로 적용한다.
- 응답 200: `Task` 배열. 조건에 맞는 항목이 없으면 `[]`.
- 허용되지 않은 status·priority 값은 422.

### POST /api/tasks  (T06)
할 일을 등록한다.

```json
{
  "title": "보고서 작성",
  "description": "1장 초안",
  "priority": "HIGH",
  "due_date": "2026-10-20"
}
```

- `title`만 필수이며 나머지는 생략하면 기본값을 쓴다. status는 항상 `TODO`로 시작한다.
- 응답 201: 등록된 `Task`.
- 검증 실패 422.

### PATCH /api/tasks/{id}  (T07)
보낸 필드만 수정하고, 보내지 않은 필드는 그대로 둔다.

```json
{ "status": "DOING", "due_date": null }
```

- 수정 가능 필드: title, description, status, priority, due_date
- `due_date`에 null을 보내면 마감일을 지운다. title·description·status·priority에 null을 보내면 422.
- 응답 200: 수정된 `Task`. 없는 id는 404, 검증 실패는 422.

### DELETE /api/tasks/{id}  (T07)
할 일을 삭제한다. 삭제 확인은 화면에서 처리한다.
- 응답 204(본문 없음). 없는 id는 404.

## 화면 제공
- FastAPI(8000)는 API(`/api/...`)와 문서(`/docs`)만 제공하고 화면 파일은 제공하지 않는다.
- Nginx(80)가 화면 파일을 제공하고 `/api/`를 App 서버(8000)로 전달한다. 화면은 `/api` 상대 경로로 API를 호출하므로 CORS 설정이 필요 없다.

## 저장 단계
- T06~T07: 서버 메모리에 저장한다. API를 재시작하면 데이터가 사라진다.
- T11부터: MariaDB에 저장하며 재시작 후에도 유지된다. API 계약은 바꾸지 않는다.
- `/api/health`는 API 프로세스 상태만 확인하며 DB 접속 여부는 확인하지 않는다.
- 단계 간 데이터는 자동 이전하지 않는다.
