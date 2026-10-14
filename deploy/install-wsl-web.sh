#!/usr/bin/env bash
# Web 서버(Nginx) 설치·업데이트. deploy/WEB-SERVER.md 1~4단계를 실행한다.
# 사용: 프로젝트 루트에서 sudo bash deploy/install-wsl-web.sh  (App 서버는 install-wsl.sh로 먼저 설치)
# 커밋된 화면 파일(HEAD의 frontend)만 배포된다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WEB_DIR=/var/www/task-flow
SITE=task-flow-web
ARCHIVE=/tmp/task-flow-web.tar.gz

if [[ $EUID -ne 0 ]]; then
  echo "sudo로 실행하세요: sudo bash deploy/install-wsl-web.sh" >&2
  exit 1
fi

echo "[1] Nginx 설치"
command -v nginx >/dev/null || apt-get install -y nginx

echo "[2] 정적 파일 → $WEB_DIR"
git -C "$REPO" -c safe.directory="$REPO" archive --format=tar.gz -o "$ARCHIVE" HEAD frontend
rm -rf "$WEB_DIR"
mkdir -p "$WEB_DIR"
tar -xzf "$ARCHIVE" -C "$WEB_DIR" --strip-components=1

echo "[3] 사이트 설정 (default는 연결만 해제)"
cp "$REPO/deploy/$SITE.conf" "/etc/nginx/sites-available/$SITE"
ln -sf "/etc/nginx/sites-available/$SITE" "/etc/nginx/sites-enabled/$SITE"
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/task-flow   # 이전 이름(task-flow)으로 연결한 사이트 정리
nginx -t
systemctl enable nginx
systemctl reload nginx

echo "[4] 확인"
curl -s -o /dev/null -w "/ %{http_code}\n" http://127.0.0.1/
curl -s -w " %{http_code}\n" http://127.0.0.1/api/health
