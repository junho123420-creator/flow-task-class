# App 서버 설치 절차 (T13)

FastAPI 앱을 `/opt/task-flow`에 설치하고 `task-flow` 계정으로 systemd 서비스(`task-flow-api.service`)를 실행한다.
코드는 GitHub push 없이 `git archive`로 묶어서 전달한다. 모든 명령은 프로젝트 루트(개발 폴더)에서 실행한다.
아래 1~7단계는 `sudo bash deploy/install-wsl.sh`로 한 번에 실행할 수 있다.

## 준비
- MariaDB 실행 중, `task_flow` DB와 `task_flow_app` 사용자 존재(T09~T12).
- 프로젝트 루트에 `.env` 작성(`.env.example` 참고). `.env`는 Git에 올리지 않는다.

## 1. 실행 계정
```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin task-flow
```

## 2. 코드 묶기 (git archive)
커밋된 코드만 묶인다. 커밋하지 않은 변경은 포함되지 않는다. 화면(frontend)은 Web 서버가 제공하므로 넣지 않는다(deploy/WEB-SERVER.md).
```bash
git archive --format=tar.gz -o /tmp/task-flow.tar.gz HEAD backend requirements.txt
```

## 3. 설치
```bash
sudo mkdir -p /opt/task-flow
sudo rm -rf /opt/task-flow/backend /opt/task-flow/frontend   # 업데이트 시 지워진 파일이 남지 않게 한다(frontend는 이전 설치분 정리)
sudo tar -xzf /tmp/task-flow.tar.gz -C /opt/task-flow
```

## 4. 가상환경
```bash
sudo python3 -m venv /opt/task-flow/.venv
sudo /opt/task-flow/.venv/bin/pip install -r /opt/task-flow/requirements.txt
```

## 5. 환경변수 (.env, 권한 600)
```bash
sudo install -m 600 -o task-flow -g task-flow .env /opt/task-flow/.env
```

## 6. systemd 등록·시작
```bash
sudo cp deploy/task-flow-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable task-flow-api.service
sudo systemctl restart task-flow-api.service
```

## 7. 확인
```bash
systemctl status task-flow-api.service --no-pager      # active (running), User task-flow
curl -i http://127.0.0.1:8000/api/health                # 200 {"status":"ok"}
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/tasks   # 200 (DB 연결)
sudo systemctl stop task-flow-api.service && sudo systemctl start task-flow-api.service
journalctl -u task-flow-api.service -n 20 --no-pager    # 오류 확인
```

## 코드 업데이트
커밋 → `sudo bash deploy/install-wsl.sh` (또는 2·3단계 → requirements.txt가 바뀌었으면 4단계 → `sudo systemctl restart task-flow-api.service`)
