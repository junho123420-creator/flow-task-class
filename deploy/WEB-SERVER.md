# Web 서버 설치 절차 (T14)

Nginx가 정적 파일(`/var/www/task-flow`)을 제공하고 `/api/` 요청만 App 서버(`127.0.0.1:8000`, task-flow-api.service)로 넘긴다.
App 서버는 deploy/APP-SERVER.md로 먼저 설치한다. 모든 명령은 프로젝트 루트(개발 폴더)에서 실행한다.
아래 1~4단계는 `sudo bash deploy/install-wsl-web.sh`로 한 번에 실행할 수 있다.

## 1. Nginx 설치
```bash
sudo apt install -y nginx
```

## 2. 정적 파일 (git archive)
커밋된 frontend만 묶인다.
```bash
git archive --format=tar.gz -o /tmp/task-flow-web.tar.gz HEAD frontend
sudo rm -rf /var/www/task-flow
sudo mkdir -p /var/www/task-flow
sudo tar -xzf /tmp/task-flow-web.tar.gz -C /var/www/task-flow --strip-components=1
```

## 3. 사이트 설정
기본 사이트(default)는 연결만 끊고 파일은 남긴다.
```bash
sudo cp deploy/task-flow-web.conf /etc/nginx/sites-available/task-flow-web
sudo ln -sf /etc/nginx/sites-available/task-flow-web /etc/nginx/sites-enabled/task-flow-web
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

## 4. 확인
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/            # 200 (index.html)
curl -i http://127.0.0.1/api/health                                    # 200 {"status":"ok"}
```
- 브라우저 `http://localhost/`에서 할 일 등록 → `mariadb`에서 SELECT로 저장 확인.
- `sudo systemctl restart task-flow-api.service` 후 새로고침 → 목록 유지.
- App 중지 시(`sudo systemctl stop task-flow-api.service`) `/api/` 요청은 502, 화면은 오류 문구 표시.

## 정적 파일 업데이트
커밋 → `sudo bash deploy/install-wsl-web.sh` 또는 2단계 (Nginx 재시작 불필요)
