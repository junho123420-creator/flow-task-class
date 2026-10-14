"""회원가입·로그인·세션 처리(T17). 비밀번호와 세션 토큰의 원문은 DB에 저장하지 않는다."""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal
from .models import SessionRow, UserRow
from .schemas import User

SESSION_COOKIE = "task_flow_session"
SESSION_DAYS = 7
SESSION_MAX_AGE = SESSION_DAYS * 24 * 60 * 60

LOGIN_REQUIRED = "로그인이 필요합니다."
LOGIN_FAILED = "아이디 또는 비밀번호가 올바르지 않습니다."
USERNAME_TAKEN = "이미 사용 중인 아이디입니다."

# scrypt 설정(N=2^14, r=8, p=1). 해시 문자열에 함께 저장해 나중에 설정을 바꿔도 기존 해시를 확인할 수 있다.
SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DKLEN = 2**14, 8, 1, 64


def utc_now() -> datetime:
    """DB에는 시간대 정보 없는 UTC 일시를 초 단위로 저장한다."""
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)


def to_user(row: UserRow) -> User:
    return User(id=row.id, username=row.username, created_at=row.created_at.replace(tzinfo=timezone.utc))


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    """'scrypt$N$r$p$salt$hash' 형식으로 반환한다."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_DKLEN
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = stored.split("$")
        if algorithm != "scrypt":
            return False
        expected_bytes = base64.b64decode(expected)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_bytes),
        )
    except ValueError:
        return False
    return hmac.compare_digest(digest, expected_bytes)


# 없는 아이디로 로그인할 때도 같은 시간이 걸리도록 비교에 쓰는 해시(아이디 존재 여부를 응답 시간으로 알 수 없게 한다).
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


class DbAuthStore:
    """users·sessions 테이블로 가입·로그인·로그아웃을 처리한다."""

    def signup(self, username: str, password: str) -> User | None:
        """가입한 사용자를 반환한다. 아이디가 이미 있으면 None."""
        row = UserRow(username=username, password_hash=hash_password(password), created_at=utc_now())
        try:
            with SessionLocal() as session, session.begin():
                session.add(row)
                session.flush()
                return to_user(row)
        except IntegrityError:
            # users.username UNIQUE 제약 위반(동시에 같은 아이디로 가입한 경우 포함).
            return None

    def login(self, username: str, password: str) -> tuple[User, str] | None:
        """맞으면 (사용자, 세션 토큰 원문)을 반환한다. 아이디가 없거나 비밀번호가 틀리면 None."""
        with SessionLocal() as session, session.begin():
            row = session.scalars(select(UserRow).where(UserRow.username == username)).first()
            # 아이디가 정확히 같을 때만 인정한다(DB 정렬 규칙의 대소문자 무시 비교에 기대지 않는다).
            if row is None or row.username != username:
                verify_password(password, _DUMMY_HASH)
                return None
            if not verify_password(password, row.password_hash):
                return None
            now = utc_now()
            # 이 사용자의 만료된 세션은 로그인할 때 정리한다.
            session.execute(delete(SessionRow).where(SessionRow.user_id == row.id, SessionRow.expires_at <= now))
            token = secrets.token_urlsafe(32)
            session.add(
                SessionRow(
                    token_hash=hash_token(token),
                    user_id=row.id,
                    created_at=now,
                    expires_at=now + timedelta(days=SESSION_DAYS),
                )
            )
            return to_user(row), token

    def logout(self, token: str) -> None:
        with SessionLocal() as session, session.begin():
            session.execute(delete(SessionRow).where(SessionRow.token_hash == hash_token(token)))

    def user_for_token(self, token: str) -> User | None:
        """만료되지 않은 세션의 사용자를 반환한다. 만료 시각은 연장하지 않는다."""
        statement = (
            select(UserRow)
            .join(SessionRow, SessionRow.user_id == UserRow.id)
            .where(SessionRow.token_hash == hash_token(token), SessionRow.expires_at > utc_now())
        )
        with SessionLocal() as session:
            row = session.scalars(statement).first()
            return to_user(row) if row is not None else None


auth_store = DbAuthStore()


def current_user(request: Request) -> User:
    """로그인이 필요한 API의 의존성. 세션 쿠키가 없거나 만료·로그아웃되었으면 401."""
    token = request.cookies.get(SESSION_COOKIE)
    user = auth_store.user_for_token(token) if token else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=LOGIN_REQUIRED)
    return user
