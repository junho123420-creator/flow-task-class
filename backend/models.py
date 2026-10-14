from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

TABLE_ARGS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

# 공개 범위와 팀 지정이 서로 맞아야 한다: PRIVATE은 팀 없음, TEAM은 팀 필수.
TASK_TEAM_CHECK = "(visibility = 'PRIVATE' AND team_id IS NULL) OR (visibility = 'TEAM' AND team_id IS NOT NULL)"


class UserRow(Base):
    """users 테이블. 비밀번호는 원문이 아닌 scrypt 해시만 저장한다."""

    __tablename__ = "users"
    __table_args__ = TABLE_ARGS

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SessionRow(Base):
    """sessions 테이블. 쿠키의 토큰 원문은 저장하지 않고 SHA-256 해시(16진수 64자)만 저장한다."""

    __tablename__ = "sessions"
    __table_args__ = TABLE_ARGS

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TeamRow(Base):
    """teams 테이블. owner_id는 팀장이다."""

    __tablename__ = "teams"
    __table_args__ = TABLE_ARGS

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TeamMemberRow(Base):
    """team_members 테이블. 팀장도 멤버로 저장한다."""

    __tablename__ = "team_members"
    __table_args__ = TABLE_ARGS

    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TaskRow(Base):
    """tasks 테이블. 값 규칙은 API-SPEC.md의 Task 객체와 같다."""

    __tablename__ = "tasks"
    __table_args__ = (CheckConstraint(TASK_TEAM_CHECK, name="ck_tasks_team"), TABLE_ARGS)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="", server_default="")
    status: Mapped[str] = mapped_column(
        Enum("TODO", "DOING", "DONE", name="task_status"),
        nullable=False,
        default="TODO",
        server_default="TODO",
    )
    priority: Mapped[str] = mapped_column(
        Enum("HIGH", "NORMAL", "LOW", name="task_priority"),
        nullable=False,
        default="NORMAL",
        server_default="NORMAL",
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # UTC 기준 등록 일시. 시간대 정보 없이 저장하고 API 응답에서 UTC로 표시한다.
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # T16: 작성자. T14 이전에 등록된 행은 작성자가 없어(NULL) 어떤 사용자에게도 표시하지 않는다.
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", name="fk_tasks_owner"), nullable=True)
    visibility: Mapped[str] = mapped_column(
        Enum("PRIVATE", "TEAM", name="task_visibility"),
        nullable=False,
        default="PRIVATE",
        server_default="PRIVATE",
    )
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", name="fk_tasks_team"), nullable=True)
