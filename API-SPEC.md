# Task Flow API 명세

PRD.md의 요구사항을 API 계약으로 정리한다. 구현 순서는 PLAN.md를 따른다.
T05~T14는 단일 사용자 계약이고, T15부터 다중 사용자·팀 계약(PRD F10~F16)으로 바꾼다.

## 공통
- 기본 주소: `http://127.0.0.1:8000` (개발), 모든 경로는 `/api`로 시작한다.
- 요청·응답 본문은 JSON(UTF-8)이다.
- 날짜는 `YYYY-MM-DD`, 일시는 ISO 8601 UTC 문자열(예: `2026-10-13T05:12:30Z`)이다.
- 오류 응답은 FastAPI 기본 형식 `{"detail": ...}`을 사용한다.
- 정의되지 않은 필드를 보내면 422로 거절한다(모든 요청 본문 공통).

| 상태 코드 | 의미 |
|---|---|
| 200 | 조회·수정 성공 |
| 201 | 등록 성공 |
| 204 | 삭제·로그아웃 성공(본문 없음) |
| 401 | 로그인 필요(세션 없음·만료·로그아웃됨) 또는 로그인 실패. `{"detail": "로그인이 필요합니다."}` |
| 403 | 볼 수는 있지만 그 작업 권한이 없음(작성자만, 팀장만 가능한 작업) |
| 404 | 대상이 없거나 볼 수 없음(남의 PRIVATE 할 일, 속하지 않은 팀 포함) |
| 409 | 중복(아이디, 팀 이름, 이미 팀 멤버) |
| 422 | 입력값 검증 실패 |
| 503 | DB 연결 실패 또는 DB 처리 오류. 응답: `{"detail": "DB에 연결할 수 없거나 처리 중 오류가 발생했습니다."}` |

- 볼 수 없는 대상은 존재 여부를 알 수 없도록 403이 아닌 404로 응답한다.

## 인증 (F10~F12)

### 세션 쿠키
- 이름 `task_flow_session`, 속성 `HttpOnly; SameSite=Lax; Path=/; Max-Age=604800`(7일).
- 값은 서버가 `secrets`로 만든 임의 토큰이다. DB에는 토큰의 SHA-256 해시, 사용자 id, 만료 시각만 저장한다.
- 만료 시각은 로그인 시점부터 7일로 고정한다(사용해도 연장하지 않음). 만료된 세션은 401.
- HTTP(학습 환경)라 `Secure` 속성은 붙이지 않는다. HTTPS 배포 시 추가한다.
- 화면과 API가 같은 주소(Nginx)이고 CORS를 허용하지 않으므로, 다른 사이트에서 이 API로 요청을 보낼 수 없다.

### 로그인이 필요 없는 경로
`GET /api/health`, `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`, `/docs`, `/openapi.json`.
그 외 `/api` 경로는 로그인이 필요하며, 없으면 401이다.

### User 객체

| 필드 | 타입 | 설명 |
|---|---|---|
| id | 정수 | 서버가 발급 |
| username | 문자열 | 영문 소문자·숫자·밑줄 3~30자, 중복 불가 |
| created_at | 문자열 | 가입 UTC 일시 |

```json
{ "id": 1, "username": "alice", "created_at": "2026-10-14T05:00:00Z" }
```

### POST /api/auth/signup  (T17)
```json
{ "username": "alice", "password": "correct-horse-1" }
```
- username: `^[a-z0-9_]{3,30}$`. 대문자·공백은 자동 변환하지 않고 422.
- password: 8~128자. 앞뒤 공백을 지우지 않고 그대로 사용한다. 원문은 저장·기록하지 않고 scrypt 해시만 저장한다.
- 응답 201: `User`. 가입만 하고 로그인하지 않는다(세션 쿠키 없음). 이후 `POST /api/auth/login`으로 로그인한다.
- 아이디 중복 409 `{"detail": "이미 사용 중인 아이디입니다."}`, 형식 위반 422.

### POST /api/auth/login  (T17)
```json
{ "username": "alice", "password": "correct-horse-1" }
```
- 응답 200: `User`와 세션 쿠키.
- 없는 아이디와 틀린 비밀번호는 같은 401 `{"detail": "아이디 또는 비밀번호가 올바르지 않습니다."}`.
- 로그인 실패 횟수 제한은 하지 않는다(PRD 제외 기능).

### POST /api/auth/logout  (T17)
- 현재 세션을 DB에서 지우고 쿠키를 삭제한다. 응답 204.
- 로그인하지 않은 상태에서도 204(같은 결과).

### GET /api/auth/me  (T17)
- 응답 200: 로그인한 `User`. 로그인하지 않았으면 401.

## 팀 (F16)

### Team 객체

| 필드 | 타입 | 설명 |
|---|---|---|
| id | 정수 | 서버가 발급 |
| name | 문자열 | 앞뒤 공백 제거 후 1~50자, 중복 불가 |
| owner | 객체 | 팀장 `{"id", "username"}` |
| created_at | 문자열 | 생성 UTC 일시 |

### Member 객체

| 필드 | 타입 | 설명 |
|---|---|---|
| user | 객체 | `{"id", "username"}` |
| is_owner | 불리언 | 팀장 여부 |
| joined_at | 문자열 | 멤버가 된 UTC 일시 |

### POST /api/teams  (T18)
```json
{ "name": "개발팀" }
```
- 만든 사람이 팀장이 되고 멤버로도 저장된다. 응답 201: `Team`.
- 이름 중복 409 `{"detail": "이미 사용 중인 팀 이름입니다."}`, 형식 위반 422.

### GET /api/teams  (T18)
- 내가 속한 팀 목록(id 오름차순). 응답 200: `Team` 배열.

### GET /api/teams/{team_id}/members  (T18)
- 그 팀의 멤버만 조회한다. 응답 200: `Member` 배열(팀장 먼저, 이후 가입 순).
- 내가 속하지 않은 팀·없는 팀은 404 `{"detail": "팀을 찾을 수 없습니다."}`.

### POST /api/teams/{team_id}/members  (T18)
```json
{ "username": "bob" }
```
- 팀장만 아이디로 멤버를 추가한다. 응답 201: 추가된 `Member`.
- 팀 멤버가 아니면 404, 멤버지만 팀장이 아니면 403 `{"detail": "팀장만 할 수 있습니다."}`.
- 없는 아이디 404 `{"detail": "사용자를 찾을 수 없습니다."}`, 이미 멤버 409 `{"detail": "이미 팀 멤버입니다."}`.

### DELETE /api/teams/{team_id}/members/{user_id}  (T18)
- 팀장은 다른 멤버를 제거하고, 멤버는 자기 자신을 지워 팀을 떠난다. 응답 204.
- 팀 멤버가 아니면 404. 팀장이 아닌 멤버가 다른 멤버를 지우면 403.
- 팀장 자신은 떠나거나 제거될 수 없다: 409 `{"detail": "팀장은 팀을 떠날 수 없습니다."}`.
- 대상 user_id가 그 팀 멤버가 아니면 404.
- 떠난 멤버는 그 팀의 TEAM 할 일을 더 이상 볼 수 없다. 단, 자기가 작성한 할 일은 계속 본다.
- 떠난 멤버가 작성한 TEAM 할 일은 그 팀에 그대로 남아 팀 멤버가 계속 보고 수정한다.

## 할 일 (F01~F09, F13~F15)

### 볼 수 있는 할 일
로그인한 사용자 U에게 할 일 T가 보이는 조건:
- T의 작성자가 U이다. 또는
- T가 `TEAM`이고 U가 T의 팀 멤버이다.

작성자가 없는 기존 할 일(T14 이전 데이터)은 누구에게도 보이지 않는다. 볼 수 없는 할 일은 모든 엔드포인트에서 404.

### Task 객체

| 필드 | 타입 | 규칙 | 기본값 |
|---|---|---|---|
| id | 정수 | 서버가 발급하는 고유 값. 수정·삭제는 id로 처리한다. | - |
| title | 문자열 | 앞뒤 공백 제거 후 1~100자 | 필수 |
| description | 문자열 | 최대 2000자 | `""` |
| status | 문자열 | `TODO`, `DOING`, `DONE` | `TODO` |
| priority | 문자열 | `HIGH`, `NORMAL`, `LOW` | `NORMAL` |
| due_date | 문자열 또는 null | 실제 존재하는 `YYYY-MM-DD` 날짜, 미지정은 null | `null` |
| created_at | 문자열 | 등록 시 서버가 기록하는 UTC 일시 | - |
| owner | 객체 | 작성자 `{"id", "username"}`. 서버가 로그인 사용자로 기록 | - |
| visibility | 문자열 | `PRIVATE`, `TEAM` | `PRIVATE` |
| team | 객체 또는 null | TEAM이면 `{"id", "name"}`, PRIVATE이면 null | `null` |

```json
{
  "id": 1,
  "title": "보고서 작성",
  "description": "",
  "status": "TODO",
  "priority": "HIGH",
  "due_date": "2026-10-20",
  "created_at": "2026-10-13T05:12:30Z",
  "owner": { "id": 1, "username": "alice" },
  "visibility": "TEAM",
  "team": { "id": 3, "name": "개발팀" }
}
```

- 지연 여부는 사용자의 로컬 날짜가 필요하므로 API가 아닌 화면에서 계산한다.
- 작성자인지는 화면에서 `owner.id`와 `GET /api/auth/me`의 `id`를 비교해 판단한다(권한 확인은 서버가 한다).

### GET /api/health  (T05)
API 서버 상태를 확인한다. 로그인 필요 없음.
- 응답 200: `{"status": "ok"}`

### GET /api/tasks  (T06·T07, 범위 필터는 T19)
볼 수 있는 할 일을 등록 순서(id 오름차순)로 반환한다.

| 쿼리 | 설명 |
|---|---|
| q | 제목에 포함된 글자(대소문자 무시, 앞뒤 공백 제거). 비어 있으면 조건 없음 |
| status | `TODO`, `DOING`, `DONE` 중 하나 |
| priority | `HIGH`, `NORMAL`, `LOW` 중 하나 |
| scope | `all`(기본, 볼 수 있는 전체), `mine`(내가 작성), `team`(특정 팀의 TEAM 할 일) |
| team_id | `scope=team`일 때 필수. 내가 속한 팀이어야 한다 |

- 여러 조건은 AND로 적용한다.
- 응답 200: `Task` 배열. 조건에 맞는 항목이 없으면 `[]`.
- 허용되지 않은 status·priority·scope 값, `scope=team`인데 team_id 없음은 422.
- 속하지 않은 팀의 team_id는 404 `{"detail": "팀을 찾을 수 없습니다."}`.

### POST /api/tasks  (T06, 공개 범위는 T19)
할 일을 등록한다. 작성자는 로그인 사용자다.

```json
{
  "title": "보고서 작성",
  "description": "1장 초안",
  "priority": "HIGH",
  "due_date": "2026-10-20",
  "visibility": "TEAM",
  "team_id": 3
}
```

- `title`만 필수이며 나머지는 생략하면 기본값을 쓴다. status는 항상 `TODO`로 시작한다.
- `visibility=TEAM`이면 내가 속한 팀의 `team_id`가 필수다. 없거나 내가 속하지 않은 팀이면 422.
- `visibility=PRIVATE`(또는 생략)이면 `team_id`는 생략하거나 null이어야 한다. 값이 있으면 422.
- 응답 201: 등록된 `Task`. 검증 실패 422.

### PATCH /api/tasks/{id}  (T07, 권한은 T19)
보낸 필드만 수정하고, 보내지 않은 필드는 그대로 둔다.

```json
{ "status": "DOING", "due_date": null }
```

- 수정 가능 필드: title, description, status, priority, due_date, visibility, team_id
- `due_date`에 null을 보내면 마감일을 지운다. title·description·status·priority·visibility에 null을 보내면 422.
- title·description·status·priority·due_date: 볼 수 있는 사용자(작성자, TEAM이면 팀 멤버)가 수정한다.
- visibility·team_id: 작성자만 바꾼다. 작성자가 아니면 403 `{"detail": "작성자만 할 수 있습니다."}`.
  - `TEAM`으로 바꾸거나 팀을 바꾸면 내가 속한 팀의 team_id가 필요하다(없으면 422).
  - `PRIVATE`으로 바꾸면 team은 null이 된다. 이때 team_id 값을 함께 보내면 422.
- 응답 200: 수정된 `Task`. 볼 수 없거나 없는 id는 404, 검증 실패는 422.

### DELETE /api/tasks/{id}  (T07, 권한은 T19)
할 일을 삭제한다. 삭제 확인은 화면에서 처리한다.
- 작성자만 삭제한다. 볼 수 있지만 작성자가 아니면 403. 볼 수 없거나 없는 id는 404.
- 응답 204(본문 없음).

## 화면 제공
- FastAPI(8000)는 API(`/api/...`)와 문서(`/docs`)만 제공하고 화면 파일은 제공하지 않는다.
- Nginx(80)가 화면 파일을 제공하고 `/api/`를 App 서버(8000)로 전달한다. 화면은 `/api` 상대 경로로 API를 호출하므로 CORS 설정이 필요 없다.
- 세션 쿠키는 같은 주소(Nginx)에서 자동으로 전송된다.

## 저장 단계
- T06~T07: 서버 메모리에 저장한다. API를 재시작하면 데이터가 사라진다.
- T11부터: MariaDB에 저장하며 재시작 후에도 유지된다.
- T16부터: users, sessions, teams, team_members 테이블을 추가하고 tasks에 owner_id, visibility, team_id를 추가한다.
  세션도 DB에 저장하므로 API를 재시작해도 로그인이 유지된다.
- `/api/health`는 API 프로세스 상태만 확인하며 DB 접속 여부는 확인하지 않는다.
- 단계 간 데이터는 자동 이전하지 않는다. 작성자 없는 기존 할 일은 남겨 두되 표시하지 않는다.

## PRD 대응

| PRD | 이 문서 |
|---|---|
| F01~F09 | 할 일: Task 객체, GET·POST·PATCH·DELETE /api/tasks |
| F10 | POST /api/auth/signup, User 객체 |
| F11 | POST /api/auth/login·logout, 세션 쿠키(7일 고정) |
| F12 | 로그인이 필요 없는 경로 외 401, GET /api/auth/me |
| F13 | 볼 수 있는 할 일, visibility PRIVATE, 404 |
| F14 | visibility TEAM·team_id, PATCH 권한(작성자만 visibility·team), DELETE 작성자만, 팀 떠난 뒤 접근 |
| F15 | Task의 owner·team, GET /api/tasks scope·team_id |
| F16 | /api/teams, 멤버 추가·제거·탈퇴, 팀장 규칙 |
