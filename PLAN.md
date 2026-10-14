# Task Flow PLAN
## 작업 원칙
한 번에 아래 작업 하나만 구현한다. 실제 확인 전에는 완료로 표시하지 않는다.
상태는 [ ] 미완료, [x] 확인 완료로 관리하고 확인 결과를 각 항목 아래 기록한다.
## 2장: 브라우저 앱
- [x] T01: frontend/index.html, styles.css, app.js 생성. 제목 입력·등록·목록만 구현한다.
  확인: 두 항목 등록, 빈 제목 거절. 이 단계에서 새로고침하면 사라져도 정상이다.
  기록(2026-10-13): frontend/index.html, styles.css, app.js 생성.
  Node DOM 스텁 테스트 통과(두 항목 등록, 빈·공백 제목 거절, 101자 거절, 100자 등록, HTML 글자 표시).
  http.server 5500에서 세 파일 200 응답.
  Windows 브라우저(http://localhost:5500, WSL localhostForwarding)에서 사용자 확인 정상. 남은 오류 없음.
- [x] T02: localStorage(task-flow-v1) 저장·복원.
  확인: 새로고침 후 유지. 손상된 저장값을 자동 덮어쓰지 않는다.
  기록(2026-10-13): frontend/app.js 저장·복원 추가, index.html에 저장 오류 영역·버튼 id 추가, styles.css 비활성 스타일.
  Node 스텁 테스트 통과(저장, 재실행 후 복원, 손상값 4종에서 등록 중지·원래 값 유지, 저장 실패 시 되돌림, T01 회귀).
  http.server 세 파일 200 응답.
  Windows 브라우저에서 사용자 확인 정상(새로고침 후 유지, 손상값 입력 시 등록 중지). 남은 오류 없음.
- [x] T03: 상태 변경, 수정, 삭제 확인.
  확인: 삭제 취소 시 유지. 다른 항목이 수정되지 않는다.
  기록(2026-10-13): frontend/app.js 상태 선택·제목 수정·삭제 확인 추가(id 기준), styles.css 항목 버튼·완료 스타일.
  설명 수정은 T04에서 다룬다. 저장 실패 시 변경을 되돌린다. status 없는 기존 저장값은 TODO로 읽는다.
  Node 스텁 테스트 12개 통과(상태 변경, 빈 제목 수정 거절, 수정·취소·Esc, 삭제 취소 유지, 삭제 시 해당 항목만, 재실행 후 유지, 저장 실패 되돌림, 회귀).
  Windows 브라우저에서 사용자 확인 정상(상태 변경·수정·삭제 취소·삭제, 새로고침 후 유지). 남은 오류 없음.
- [x] T04: 설명·우선순위·마감일·검색·필터·지연 표시.
  확인: 필터 중 수정·삭제, 어제 마감 TODO의 지연 표시.
  기록(2026-10-13): index.html 등록 폼(우선순위·마감일·설명)과 검색·필터 영역 추가, app.js 필드·검증·수정 폼·필터·지연 표시, styles.css 배지·필터 스타일.
  수정 폼에서 제목·설명·우선순위·마감일을 함께 수정한다. 이전 단계 저장값은 빠진 필드를 기본값으로 읽는다.
  Node 스텁 테스트 통과: T04 12개(기본값, 검증, 지연 표시, 검색·필터 AND, 필터 중 수정·삭제, 호환·손상값, 새로고침 유지), T03 회귀 12개.
  Windows 브라우저에서 사용자 확인 정상(어제 마감 TODO 지연 표시, 필터 AND, 필터 중 수정·삭제, 새로고침 유지). 남은 오류 없음.
## 3장: API
- [x] T05: API-SPEC.md 작성, FastAPI /api/health 구현.
  확인: curl로 200과 status=ok.
  기록(2026-10-13): API-SPEC.md(T05~T08 계약), backend/__init__.py, backend/main.py, requirements.txt(fastapi 0.143.0, uvicorn 0.54.0), .gitignore 생성.
  실행: .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 (Python 3.10.12)
  결과: curl -i /api/health → 200, {"status":"ok"}. /docs 200, 없는 경로 404. 남은 오류 없음.
- [x] T06: 메모리 기반 /api/tasks GET과 POST.
  확인: /docs에서 등록 후 조회. 입력 위반은 422.
  기록(2026-10-13): backend/schemas.py(TaskCreate·Task 검증), backend/store.py(메모리 저장소), backend/main.py에 GET·POST /api/tasks 추가.
  수정: due_date strict 검증이 "2026-10-20"까지 거절해 YYYY-MM-DD 형식 검사 후 날짜 변환하도록 변경.
  실행: 포트 8001에서 uvicorn 실행 후 urllib 스크립트로 확인. 26개 통과(기본값 201, 경계값 201, 위반 18종 422, GET id 순서, 재시작 후 빈 목록).
  /docs 화면에서 사용자 확인 정상(등록 201, 빈 제목 422, 등록 후 조회). 남은 오류 없음.
- [x] T07: PATCH·DELETE와 필터 구현.
  확인: 미전달 필드 유지, 없는 ID 404, 삭제 204.
  기록(2026-10-13): backend/schemas.py TaskUpdate(보낸 필드만 수정, due_date만 null 허용), backend/store.py update·delete·필터, backend/main.py PATCH·DELETE와 q·status·priority 쿼리.
  실행: 포트 8001에서 uvicorn 실행 후 urllib 스크립트로 확인. T07 41개 통과(부분 수정 시 나머지·다른 항목 유지, due_date null 삭제, PATCH 위반 14종 422, 없는 id 404, 삭제 204·재삭제 404, q·status·priority AND, 잘못된 필터 422). T06 회귀 25개 통과.
  남은 오류 없음.
- [x] T08: 프런트엔드 저장 처리를 API 호출로 교체.
  확인: 화면과 curl 목록이 같음. API 중지 시 오류 표시.
  기록(2026-10-13): frontend/app.js localStorage 제거, 목록·등록·상태 변경·수정·삭제를 /api 호출로 교체, 검색·필터는 API 쿼리(q·status·priority)로 조회, 지연 표시는 화면에서 계산.
  backend/main.py에 frontend 정적 파일 제공 추가(같은 주소, CORS 불필요), index.html 오류 영역 id를 api-error로 변경, API-SPEC.md에 화면 제공 방식 추가.
  실행: 포트 8001 uvicorn + Node 스텁(실제 HTTP 요청) 테스트 12개 통과(등록 후 화면·curl 목록 동일, 필터 중 수정·삭제, 404 안내, API 중지 시 오류 표시). T07 API 회귀 41개 통과.
  Windows 브라우저(http://localhost:8000)에서 사용자 확인 정상(화면·curl 목록 동일, API 중지 시 오류 표시). 남은 오류 없음.
## 4장: DB
- [x] T09: MariaDB 전용 사용자·DB와 .env 준비. 접속 확인.
  기록(2026-10-13): MariaDB 10.6.23(127.0.0.1:3306). 사용자가 task_flow DB와 task_flow_app@localhost 생성, .env 작성. .env.example(가짜 값) 추가, .env 권한 600, .gitignore 대상 확인.
  결과: .env 정보로 mariadb 접속 성공(CURRENT_USER task_flow_app@localhost, DATABASE task_flow, utf8mb4_general_ci, 테이블 없음).
  참고: 권한이 ALL PRIVILEGES(DROP 포함)로 부여됨. 비밀번호가 짧아 서버 분리(T12) 전 변경 권장.
- [x] T10: backend/database.py, models.py, init_db.py 생성.
  확인: python -m backend.init_db 실행 후 tasks 테이블 확인.
  기록(2026-10-13): requirements.txt에 SQLAlchemy 2.0.54, PyMySQL 1.2.3 추가. database.py(.env·환경변수 읽기, 엔진·세션), models.py(TaskRow), init_db.py(없는 테이블만 생성) 작성.
  실행: python -m backend.init_db 2회 → 1회차 생성, 2회차 "이미 있어 변경하지 않음".
  결과: DESCRIBE tasks로 id(AUTO_INCREMENT PK)·title varchar(100)·description varchar(2000)·status·priority ENUM·due_date date NULL·created_at datetime 확인. InnoDB, utf8mb4, 0행. 접속 정보 누락 시 안내 오류 확인. 남은 오류 없음.
- [x] T11: API 메모리 저장을 DB로 교체.
  확인: 등록한 행을 SQL로 조회. API 재시작 후 데이터 유지.
  기록(2026-10-13): backend/store.py를 DbTaskStore(MariaDB, 메서드 동일)로 교체, backend/main.py가 DbTaskStore 사용·DB 오류 시 503 응답. API-SPEC.md에 503 추가.
  실행: 포트 8001 uvicorn + urllib 스크립트. 31개 통과(등록·부분 수정·422·404·204, q·status·priority AND, q의 %·_ 글자 검색, 2000자 설명·이모지 저장).
  결과: 등록 행을 mariadb SELECT로 확인. API 재시작 후 같은 id·수정 내용 유지. 틀린 DB 비밀번호로 실행 시 /api/tasks 503, 로그에 비밀번호 미노출.
  테스트 항목([T11검증] 제목)은 확인 후 삭제해 tasks는 0행. AUTO_INCREMENT는 6부터 시작. 남은 오류 없음.
## 5장: 서버 분리
- [x] T12: DB 서버 구성 후 App 서버에서 SELECT 1 확인.
  기록(2026-10-14): 수업 구성에 따라 WSL 한 대에 App(FastAPI)과 DB(MariaDB)를 함께 둔다.
  DB: MariaDB 11.8.6(mariadb.service, enabled·active), 127.0.0.1:3306에서만 수신, DB task_flow, 사용자 task_flow_app@localhost.
  실행: 앱 설정(.env)으로 접속해 SELECT 1 실행.
  결과: SELECT 1 → 1, CURRENT_USER task_flow_app@localhost, DATABASE task_flow, tasks 테이블 조회 정상. 남은 오류: 없음.
- [x] T13: App 서버 코드·가상환경·환경변수·systemd 구성.
  확인: App에서 /api/health 응답.
  기록(2026-10-14): WSL을 App 서버로 사용. deploy/task-flow-api.service(/opt/task-flow, task-flow 계정, 0.0.0.0:8000,
  After=mariadb.service, Restart=on-failure), deploy/APP-SERVER.md(git archive 묶기·venv·.env 600·systemd·확인 절차) 작성.
  코드 push 없이 git archive(HEAD의 backend·frontend·requirements.txt)로 /opt/task-flow에 설치.
  실행: deploy/APP-SERVER.md 1~6단계(useradd --system task-flow, git archive → tar 해제, python3 -m venv, pip install,
        install -m 600 .env, systemd 등록 후 enable·restart).
  결과: 설치 파일과 deploy 파일 동일, enabled, active(running), 프로세스 계정 task-flow, /opt/task-flow/.env 600(task-flow 소유).
  curl /api/health → 200 {"status":"ok"}, /api/tasks → 200(DB 연결 정상). 8000은 0.0.0.0, 3306은 127.0.0.1에서만 수신. 남은 오류: 없음.
  참고(수업 범위 밖): EC2(jjh-bastion-host)에도 App+MariaDB를 올려 task-flow.service로 실행해 봄.
- [x] T14: Web 서버 Nginx와 정적 파일·/api 프록시 구성.
  확인: Web 주소로 등록, DB 저장, App 재시작 후 유지.
  기록(2026-10-14): WSL을 Web 서버로 사용(Nginx 1.28.3). deploy/task-flow.nginx.conf(이후 task-flow-web.conf로 이름 변경. 80 포트, root /var/www/task-flow,
  /api/ → http://127.0.0.1:8000 프록시), deploy/WEB-SERVER.md(설치·git archive로 정적 파일 배포·사이트 설정·확인 절차) 작성.
  실행: git archive HEAD frontend → /var/www/task-flow, sites-available/task-flow 연결, sites-enabled/default 연결 해제,
        sudo nginx -t(성공) && sudo systemctl reload nginx. 프런트엔드는 이미 /api를 호출하므로 코드 변경 없음.
  결과: http://127.0.0.1/ → 200(Task Flow 화면), /api/health → 200. Web 주소로 등록(POST 201, id 5) → DB SELECT로 행 확인.
  sudo systemctl restart task-flow-api.service(새 PID) 후 /api/tasks에 id 5 유지. /.env → 404. nginx access.log에 요청 기록.
  설치 전 사용자 권한 임시 Nginx(8088)로 같은 설정 검증: 정적 200, POST 201, 422, /.env·/backend/main.py 404.
  테스트 행(id 4, 5)은 확인 후 삭제. 남은 오류: 없음. App 중지 시: 80 화면 200, /api/health·/api/tasks 502(Nginx), 화면 문구 "요청을 처리하지 못했습니다. (HTTP 502)". App 재시작 후 /api 200으로 복구.
  추가(2026-10-14, 사용자 요청): 8000은 FastAPI(API·/docs)만 사용. backend/main.py에서 frontend StaticFiles 제공 제거,
  API-SPEC.md 화면 제공 항목 갱신, App 묶음(APP-SERVER.md·install-wsl.sh)에서 frontend 제외.
  deploy/task-flow-web.conf(이름 변경), install-wsl.sh(App 설치), install-wsl-web.sh(Web 설치) 추가.
  확인: 저장소 코드로 uvicorn 8006 실행 시 /·index.html·app.js 404, /api/health·/api/tasks·/docs·/openapi.json 200,
  등록 201·PATCH 200·삭제 204·빈 제목 422. 스크립트 bash -n 문법 확인.
  반영: 커밋(a7ca36e) 후 sudo bash deploy/install-wsl.sh, sudo bash deploy/install-wsl-web.sh 실행.
  처음 실행 시 /tmp의 기존 압축 파일(사용자 소유)에 root가 쓰지 못해 실패(fs.protected_regular=2) → 스크립트가 mktemp 임시 파일을 쓰도록 수정.
  결과: /opt/task-flow에 backend·requirements.txt만 설치(frontend 정리), sites-enabled는 task-flow-web만 연결.
  8000: / ·index.html 404, /api/health·/docs 200. 80: / ·app.js 200, /api/health 200.
  80으로 등록 201·PATCH 200·검색 조회·삭제 204·재삭제 404(테스트 행 삭제). 남은 오류: 없음.
## 6장: 다중 사용자·팀 (PRD F10~F16)
- [x] T15: API-SPEC.md에 인증·팀 API와 할 일 API 변경 사항 작성. 코드 변경 없음.
  범위: POST /api/auth/signup·login·logout, GET /api/auth/me, 세션 쿠키 규칙,
  팀: POST /api/teams, GET /api/teams(내가 속한 팀), GET /api/teams/{id}/members, POST /api/teams/{id}/members(아이디로 추가),
  DELETE /api/teams/{id}/members/{user_id}(팀장의 제거 또는 본인 탈퇴),
  할 일 응답의 owner·visibility·team, 목록 scope 필터(all·mine·team_id),
  상태 코드(401 로그인 필요, 403 권한 없음, 404 없음·볼 수 없음, 409 아이디·팀 이름 중복·이미 멤버).
  확인: PRD F10~F16과 API-SPEC 항목이 하나씩 대응한다.
  기록(2026-10-14): API-SPEC.md에 상태 코드(401·403·409), 세션 쿠키(task_flow_session, HttpOnly·SameSite=Lax·7일 고정, 토큰 해시 저장),
  인증 API 4개, User·Team·Member 객체, 팀 API 5개, 볼 수 있는 할 일 규칙, Task의 owner·visibility·team, scope·team_id 필터,
  PATCH·DELETE 권한, PRD 대응표 작성. 기존 할 일 필드 규칙·422 검증·부분 수정 계약은 유지.
  사용자 결정 반영: 가입 후 자동 로그인 안 함, 세션 7일 고정, 로그인 실패 횟수 제한 제외(PRD 제외 기능), 팀을 떠난 작성자의 TEAM 할 일은 팀에 남음.
  확인: PRD F10~F16 각각 API-SPEC 대응표 행 존재, 주요 규칙(아이디 형식, 비밀번호 길이, 쿠키 속성, 같은 401, 404/403 구분, 팀장 규칙,
  작성자 없는 기존 행 미표시) 문구 확인. 남은 오류: 없음.
  참고: T19에서 할 일 API에 로그인을 적용하면 T20(로그인 화면) 전까지 현재 화면은 401로 목록을 불러오지 못한다.
- [x] T16: users·sessions·teams·team_members 테이블 추가, tasks에 owner_id(NULL 허용)·visibility(기본 PRIVATE)·team_id(NULL 허용) 추가.
  기존 테이블·행은 삭제하지 않는다. 변경 전 mysqldump 백업. 변경은 별도 스크립트(backend/migrate_*.py)로 한 번만 적용.
  확인: SHOW CREATE TABLE로 새 열·외래키·인덱스·유일 제약 확인, 기존 행 수 유지, 스크립트 재실행 시 변경 없음.
  기록(2026-10-14): backend/models.py(UserRow·SessionRow·TeamRow·TeamMemberRow 추가, TaskRow에 owner_id·visibility·team_id,
  CHECK ck_tasks_team: PRIVATE↔팀 없음, TEAM↔팀 필수), backend/migrate_multiuser.py(신규), backend/init_db.py(전체 테이블 생성·안내).
  실행: mariadb-dump(--single-transaction --no-tablespaces)로 ~/backups/task_flow-before-T16-20261014-132528.sql 백업(권한 600, 저장소 밖),
        python -m backend.migrate_multiuser 2회.
  결과: 1회차 새 테이블 4개 생성, tasks에 열 3개·외래키 2개·CHECK 1개 적용, 행 수 3 → 3. 2회차 모두 "변경 안 함".
  SHOW CREATE TABLE: users.username·teams.name·sessions.token_hash UNIQUE, team_members PK(team_id,user_id),
  sessions·team_members 외래키 ON DELETE CASCADE, tasks fk_tasks_owner·fk_tasks_team·ck_tasks_team.
  기존 행 id 1·3·10은 owner_id NULL, PRIVATE로 유지.
  제약 시험(트랜잭션 안에서 실행 후 롤백) 13건: 멤버 중복·아이디 중복·팀 이름 중복(대소문자만 다른 이름 포함) 거절,
  TEAM+팀 없음·PRIVATE+팀 있음 거절(CHECK), 없는 작성자·없는 팀 거절(FK), 잘못된 visibility 거절, 정상 조합 허용. 시험 후 새 테이블 0행.
  회귀: 현재 API를 8006에서 실행해 GET 200·POST 201·PATCH 200·422·DELETE 204. 실행 중인 서비스(/opt, 이전 코드) /api/tasks 200 유지.
  init_db: 새 설치용 DDL에 같은 열·제약 포함 확인, 기존 DB에서는 "이미 있어 변경하지 않았습니다".
  참고: 시험 중 롤백된 INSERT로 tasks AUTO_INCREMENT가 16 이후로 증가(데이터 영향 없음).
  참고: 팀 이름은 DB 정렬 규칙(utf8mb4_uca1400_ai_ci)상 대소문자·악센트만 다른 이름도 중복으로 처리된다.
  참고: T19 전까지 기존 화면·API로 등록한 행은 작성자가 없어(NULL) T19 이후 표시되지 않는다. 남은 오류: 없음.
- [x] T17: 회원가입·로그인·로그아웃·내 정보 API. 비밀번호는 hashlib.scrypt, 세션 토큰은 secrets로 발급하고 해시만 저장.
  쿠키: HttpOnly, SameSite=Lax, Path=/, 7일. 새 패키지 없음.
  확인: 가입 201(세션 쿠키 없음, 자동 로그인 안 함), 아이디 중복 409, 형식 위반 422, 잘못된 비밀번호와 없는 아이디 모두 같은 401, 로그인 후 me 200,
  로그아웃 후 me 401, DB에 비밀번호·토큰 원문 없음, API 재시작 후 로그인 유지.
  기록(2026-10-14): backend/auth.py(신규: scrypt 해시·검증, 세션 토큰 발급·SHA-256 해시 저장, DbAuthStore, current_user 의존성),
  backend/schemas.py(SignupRequest·LoginRequest·User), backend/main.py(POST /api/auth/signup·login·logout, GET /api/auth/me).
  없는 아이디도 더미 해시로 같은 시간 비교, 아이디는 대소문자까지 정확히 같을 때만 인정, 로그인 시 그 사용자의 만료 세션 정리.
  실행: uvicorn 8006 + 시험 스크립트(urllib), 이후 API 재시작해 같은 쿠키로 재확인.
  결과: 39건 통과. 가입 201(응답 id·username·created_at만, 쿠키 없음), 중복 409, 422 12종(대문자·2자·31자·공백·한글·하이픈,
  비밀번호 7자·129자, 모르는 필드, 누락, 숫자형, null), 경계값 201(아이디 3·30자, 비밀번호 8·128자), 거절된 가입 미저장.
  틀린 비밀번호·없는 아이디·대문자 아이디 모두 같은 401·같은 문구. 로그인 200, 쿠키 HttpOnly·SameSite=lax·Path=/·Max-Age=604800·Secure 없음.
  me 200, 쿠키 없음·가짜 토큰 401. DB: password_hash scrypt$16384$8$1$…(원문 없음), token_hash 64자(토큰과 다름), 만료=로그인+7일.
  로그아웃 204·쿠키 삭제·그 세션 401, 다른 세션 유지, 로그인 없이 로그아웃 204. 비밀번호 앞뒤 공백 그대로 사용. 만료 세션 401.
  할 일 API는 아직 로그인 없이 200(T19 범위). API 재시작 후 me 200(로그인 유지).
  시험 계정(t17*)은 확인 후 삭제(sessions CASCADE), users·sessions 0행. 남은 오류: 없음.
- [x] T18: 팀 API. 팀 생성(만든 사람이 팀장·멤버), 내 팀 목록, 멤버 목록·추가·제거, 본인 탈퇴.
  확인: 이름 중복 409, 팀장 아닌 사용자의 추가·제거 403, 없는 아이디 404, 중복 추가 409, 팀장 탈퇴·제거 거절,
  팀 밖 사용자의 멤버 목록 조회 404, 여러 팀 소속 가능.
  기록(2026-10-14): backend/teams.py(신규: DbTeamStore, 볼 수 없는 팀은 404), backend/schemas.py(TeamCreate·MemberAdd·UserRef·Team·Member),
  backend/main.py(POST·GET /api/teams, GET·POST /api/teams/{id}/members, DELETE /api/teams/{id}/members/{user_id}, 모두 로그인 필요).
  API-SPEC.md: 멤버 아닌 대상 제거 404 문구("팀 멤버를 찾을 수 없습니다.") 추가.
  실행: uvicorn 8006 + 시험 스크립트(계정 A 팀장, B·D 멤버, C 팀 밖).
  결과: 48건 통과. 로그인 없이 5개 엔드포인트 401. 팀 생성 201(이름 앞뒤 공백 제거, owner=A), 이름 중복·대소문자만 다른 이름 409,
  422 6종(빈 이름·공백만·51자·모르는 필드·누락·null), 50자 201. 내 팀 목록(추가 전 B는 []), 멤버 목록 팀장 먼저·추가 순서.
  팀 밖·없는 팀 멤버 조회 404. 멤버 추가 201, 이미 멤버 409, 없는 아이디·대문자 아이디 404, 팀장 아닌 멤버 403, 팀 밖 404, 모르는 필드 422.
  여러 팀 소속(B: 개발팀·디자인팀). 제거: 팀장 아닌 멤버 403(팀장 제거 시도 포함), 팀 밖 404, 팀장 제거 204 → 제거된 D는 조회 404·목록 [].
  팀장 본인 탈퇴 409, 멤버 아닌 대상·없는 사용자 404, 멤버 본인 탈퇴 204 → 조회 404, 재추가 201. 로그아웃 후 401.
  회귀: T17 인증 시험 38건 통과. 시험 계정·팀 삭제(users·teams·team_members·sessions 0행). 남은 오류: 없음.
- [x] T19: 할 일 API에 로그인·권한 적용. 로그인 없으면 401. 등록 시 owner_id=로그인 사용자.
  목록은 내 할 일 + 내가 속한 팀의 TEAM 할 일(작성자 없는 기존 행 제외), scope 필터. 볼 수 없는 할 일은 404.
  TEAM 지정은 작성자가 속한 팀만 가능(아니면 422). TEAM 할 일은 팀 멤버가 수정, 삭제·visibility·team 변경은 작성자만(그 외 403).
  확인: 세 계정(A·B 같은 팀, C 팀 밖)으로 조회·수정·삭제 권한 표, 팀에서 제거된 멤버의 접근 404,
  기존 T06~T11 입력 검증(422) 회귀, 기존 작성자 없는 행 미표시.
  기록(2026-10-14): backend/store.py(볼 수 있는 조건: 작성자 또는 내가 속한 팀의 TEAM, 작성자·팀 함께 조회, 등록 시 owner_id,
  visibility·team_id 변경은 작성자만 403, 속하지 않은 팀 지정 422, 삭제는 작성자만 403, scope·team_id 필터),
  backend/schemas.py(Visibility·Scope·TeamRef, TaskCreate·TaskUpdate에 visibility·team_id, Task에 owner·visibility·team),
  backend/main.py(할 일 API 4개에 current_user). API-SPEC.md: scope가 team이 아닌데 team_id 있음 422, team_id만 보낸 PATCH 규칙 명시.
  실행: uvicorn 8006 + 시험 스크립트(A·B 같은 팀, C 팀 밖, A의 두 번째 팀 T3, C의 팀 T2).
  처음 실행 시 1건 실패: PRIVATE 할 일에 team_id만 보낸 PATCH가 422가 아닌 200(팀 지정이 조용히 무시됨) → store.update 수정 후 재실행.
  결과: 74건 통과. 로그인 없이 4개 401. 등록 201(owner=A, PRIVATE·team null / TEAM·team{id,name}), 등록 422 6종(TEAM인데 팀 없음,
  PRIVATE인데 팀, 잘못된 visibility, owner_id 지정, 없는 팀, 속하지 않은 팀). 목록: A=내 것+팀 할 일, B=팀 할 일+내 개인, C=내 개인만,
  작성자 없는 기존 행(id 1·3·10) 미표시·수정 404, scope=mine·team, 속하지 않은 팀 scope 404, scope 관련 422 3종, q·상태·우선순위·범위 AND.
  권한: 남의 PRIVATE 수정·삭제 404, 팀 밖 수정 404, 팀 멤버 내용 수정 200, 멤버의 공개 범위·팀 변경·삭제 403(이후 그대로),
  작성자 PRIVATE 전환 → 멤버에게 사라짐·404, TEAM 전환 → 보임, team_id만으로 팀 변경, 속하지 않은 팀 422, PRIVATE에 team_id만 422,
  PATCH 422 5종. 팀에서 제거된 B: 팀 할 일 404, 자기 TEAM 할 일은 보이고 수정 가능, 그 할 일은 팀에 남아 A가 봄·수정.
  회귀(T06~T07): 등록 422 8종, 경계값 201(제목 100자·설명 2000자·윤년), PATCH 422 3종, due_date null 삭제·다른 필드 유지, 없는 id 404.
  삭제: 떠난 작성자 자기 할 일 204, 작성자 204, 재삭제 404. 로그아웃 후 401.
  T17·T18 재실행: 각각 "할 일 API 로그인 없이 200" 1건만 401로 달라짐(이번 작업의 의도된 변경), 나머지 통과.
  시험 데이터 삭제 후 users·teams·sessions 0행, tasks는 기존 3행(1·3·10)만. 남은 오류: 없음.
  참고: 이제 할 일 API에 로그인이 필요해 T20 전까지 저장소 코드의 화면은 목록을 불러오지 못한다(시스템 반영은 T22).
- [x] T20: 프런트엔드 로그인·회원가입 화면, 로그아웃 버튼, 로그인 사용자 표시, 401 응답 시 로그인 화면 전환.
  확인: 브라우저에서 가입·로그인·로그아웃·새로고침 후 로그인 유지, 잘못된 로그인 문구, 아이디 글자 표시.
  기록(2026-10-14): 사용자 결정: 한 페이지 안에서 화면만 바꾸되 일반 웹사이트처럼 주소(#/login, #/signup, #/)로 구분해
  뒤로가기·앞으로가기·새로고침·주소 직접 입력이 동작하게 한다.
  frontend/index.html(머리글에 아이디·로그아웃, 로그인·회원가입 화면, 기존 할 일 화면을 tasks-view로 감쌈),
  frontend/styles.css(인증 화면·머리글, [hidden] 우선 규칙), frontend/app.js(주소별 화면 전환·탭 제목, 로그인 여부에 맞지 않는 주소는
  자동 이동(기록 안 남김), 처음 열 때 /api/auth/me 확인, 가입 후 로그인 화면에 아이디 채움, 401이면 상태 초기화 후 로그인 화면, 로그아웃 시 이전 사용자 화면 상태 삭제).
  실행: uvicorn 8006 + 사용자 권한 임시 Nginx(8088, 저장소 frontend 제공·/api 프록시) + 헤드리스 Chromium(Playwright, 시험 전용 가상환경, 프로젝트 의존성 아님).
  처음 실행 시 실패: (1) 로그아웃 상태에서도 사용자 영역이 보임 — CSS display:flex가 hidden 속성을 덮어씀 → [hidden]{display:none!important} 추가.
  (2) 시험 스크립트의 대기 순서 문제 2건(앱 동작은 정상) → 시험 수정.
  결과: 30건 통과. 미로그인 / → #/login·제목 "로그인 - Task Flow", 회원가입 링크·뒤로가기·앞으로가기, 가입 화면 검증(대문자 아이디·짧은 비밀번호),
  가입 성공 → 로그인 화면(자동 로그인 없음)·안내·아이디 채움, 중복 아이디 409 문구, 틀린 비밀번호 401 문구·비밀번호 칸 비움,
  로그인 → #/·제목·아이디 표시, 세션 쿠키 HttpOnly(document.cookie에 없음), 등록·HTML 입력 글자 표시(img 요소·alert 없음),
  새로고침 후 로그인·목록 유지, 로그인 상태에서 #/login·모르는 주소 → #/, 로그아웃 → 로그인 화면·목록 DOM 비움, 뒤로가기해도 할 일 화면 안 보임,
  로그아웃 후 API 401, 다른 사용자 로그인 시 이전 사용자 할 일 안 보임, 세션 삭제 후 조작 → 로그인 화면·안내·검색어·필터 초기화, 스크립트 오류 없음.
  화면 캡처로 배치 확인(헤드리스 브라우저에 한글 글꼴이 없어 한글은 네모로 보임, 앱 문제 아님).
  시험 계정·할 일 삭제, users·sessions 0행, tasks 기존 3행. 남은 오류: 없음.
  참고: 할 일 화면의 작성자·팀 표시와 삭제 버튼 숨김은 T21 범위(현재는 서버가 403으로 거절).
- [x] T21: 프런트엔드 팀 관리(팀 만들기, 멤버 추가·제거, 탈퇴)와 할 일 공개 범위·팀 선택, 작성자·팀 표시, 범위 필터.
  작성자가 아니면 삭제·공개 범위 변경 숨김(서버도 거절).
  확인: 브라우저에서 세 계정으로 PRD 완료 기준 확인, 팀 이름·아이디 등 사용자 입력 글자로 표시.
  기록(2026-10-14): frontend/index.html(머리글 메뉴 할 일·팀, 등록 폼 공개 범위·팀 선택, 범위 필터, 팀 화면 #/teams),
  frontend/styles.css(메뉴·팀·멤버·배지), frontend/app.js(내 팀 목록으로 팀 선택·범위 필터 구성, 팀이 없으면 '팀' 선택 불가·안내,
  할 일 배지(개인/팀 이름, 남의 할 일엔 작성자), 작성자만 삭제 버튼·수정 폼의 공개 범위·팀 선택(바뀐 경우에만 전송),
  팀 화면(팀 만들기, 멤버 목록, 팀장만 멤버 추가·제거, 팀원은 탈퇴, 제거·탈퇴는 확인 후), 팀에서 빠져 범위 필터가 404면 전체로 되돌림,
  로그아웃 시 팀 상태 정리). 서버 코드 변경 없음.
  실행: uvicorn 8006 + 임시 Nginx(8088) + 헤드리스 Chromium에서 세 계정(A 팀장, B 팀원, C 팀 밖)을 각각 다른 브라우저 컨텍스트로 동시 로그인.
  처음 실행 시 시험 스크립트 문제 1건(같은 주소로 이동하면 hashchange가 없어 목록이 갱신되지 않음, 사용자의 새로고침과 같은 상황) → 시험 수정.
  결과: 36건 통과. 팀 없으면 '팀' 선택 불가, #/teams 메뉴·현재 표시, 팀 만들기(이름 HTML은 글자로·공백 제거), 대소문자만 다른 이름 409 문구,
  없는 아이디 추가 오류, B 추가·제거 버튼, 팀 할 일 등록·배지, 등록 후 개인으로 초기화, B는 팀 할 일만 보이고 작성자 배지·삭제 버튼 없음·
  수정 폼에 공개 범위 없음, B의 제목·상태 수정, C는 아무것도 안 보임·팀 없음, A에게 B 수정 반영, 범위 '내 할 일'·'팀',
  A가 개인으로 전환 → B에게서 사라짐, A가 B 제거 → B의 팀 범위 필터가 전체로 돌아가고 오류 없음·팀 항목 사라짐,
  B가 떠나도 B의 팀 할 일은 A에게 보임, 팀원 화면(탈퇴만, 추가·제거 없음), B 탈퇴, A 삭제, 로그아웃 시 필터 정리, 스크립트 오류 없음.
  회귀: T20 화면 시험 30건 통과. 화면 캡처로 팀 화면·할 일 배지 배치 확인.
  시험 계정·팀·할 일 삭제, users·teams·sessions 0행, tasks 기존 3행. 남은 오류: 없음.
- [ ] T22: WSL 배포 반영(install-wsl.sh, install-wsl-web.sh)과 통합 확인.
  확인: http://localhost/에서 세 계정 시나리오, App 재시작 후 데이터·로그인 유지, 8000은 API만 제공 유지.
  기존 작성자 없는 행 정리는 백업 후 사용자 확인을 받아 진행.
## 실행 기준
T01~T04: python3 -m http.server 5500 --bind 127.0.0.1 --directory frontend
T05~T11: 가상환경에서 python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
T15~T21: 개발 확인은 테스트 포트(예: 8001)에서 uvicorn 실행. 시스템 반영은 커밋 후 deploy/install-wsl.sh·install-wsl-web.sh
실제 존재하는 파일을 확인한 뒤 명령을 실행한다.
## 기록
각 작업에 변경 파일, 실행 명령, 실제 확인 결과, 남은 오류를 기록한다.
정상 동작을 확인한 작업 단위로 Git 커밋한다.