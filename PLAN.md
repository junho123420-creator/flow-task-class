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
## 실행 기준
T01~T04: python3 -m http.server 5500 --bind 127.0.0.1 --directory frontend
T05~T11: 가상환경에서 python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
실제 존재하는 파일을 확인한 뒤 명령을 실행한다.
## 기록
각 작업에 변경 파일, 실행 명령, 실제 확인 결과, 남은 오류를 기록한다.
정상 동작을 확인한 작업 단위로 Git 커밋한다.