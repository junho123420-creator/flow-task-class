#!/usr/bin/env bash
# App 서버(FastAPI) 설치·업데이트. deploy/APP-SERVER.md 1~7단계를 실행한다.
# 사용: 프로젝트 루트에서 sudo bash deploy/install-wsl.sh
# 커밋된 코드(HEAD)만 설치된다. 화면(frontend)은 Web 서버가 제공하므로 넣지 않는다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR=/opt/task-flow
SERVICE=task-flow-api.service

if [[ $EUID -ne 0 ]]; then
  echo "sudo로 실행하세요: sudo bash deploy/install-wsl.sh" >&2
  exit 1
fi
if [[ ! -f "$REPO/.env" ]]; then
  echo "$REPO/.env 가 없습니다. .env.example을 참고해 먼저 작성하세요." >&2
  exit 1
fi

echo "[1] 실행 계정"
id task-flow >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin task-flow

# 실행할 때마다 새 임시 파일을 쓴다(/tmp의 다른 사용자 파일은 root도 덮어쓸 수 없다: fs.protected_regular).
ARCHIVE="$(mktemp --suffix=.tar.gz)"
trap 'rm -f "$ARCHIVE"' EXIT

echo "[2] 코드 묶기 (HEAD: backend, requirements.txt)"
git -C "$REPO" -c safe.directory="$REPO" archive --format=tar.gz -o "$ARCHIVE" HEAD backend requirements.txt

echo "[3] 설치 → $APP_DIR"
mkdir -p "$APP_DIR"
rm -rf "$APP_DIR/backend" "$APP_DIR/frontend"
tar -xzf "$ARCHIVE" -C "$APP_DIR"

echo "[4] 가상환경"
[[ -x "$APP_DIR/.venv/bin/python" ]] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "[5] .env (권한 600)"
install -m 600 -o task-flow -g task-flow "$REPO/.env" "$APP_DIR/.env"

echo "[6] systemd 등록·재시작"
cp "$REPO/deploy/$SERVICE" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

echo "[7] 확인"
for _ in $(seq 20); do
  curl -fs http://127.0.0.1:8000/api/health >/dev/null && break
  sleep 0.5
done
systemctl is-active "$SERVICE"
curl -s -w " %{http_code}\n" http://127.0.0.1:8000/api/health
curl -s -o /dev/null -w "/api/tasks %{http_code}\n" http://127.0.0.1:8000/api/tasks
