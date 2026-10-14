from datetime import datetime, timezone
from enum import Enum

from fastapi import HTTPException, status as http_status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import TaskRow, TeamMemberRow, TeamRow, UserRow
from .schemas import Priority, Scope, Status, Task, TaskCreate, TeamRef, User, UserRef, Visibility
from .teams import TEAM_NOT_FOUND

OWNER_ONLY = "작성자만 할 수 있습니다."
NOT_TEAM_MEMBER = "속한 팀만 지정할 수 있습니다."
TEAM_ID_WITHOUT_TEAM = "공개 범위가 TEAM인 할 일만 팀을 바꿀 수 있습니다."
TEAM_ID_REQUIRED = "scope=team이면 team_id가 필요합니다."
TEAM_ID_ONLY_FOR_TEAM_SCOPE = "team_id는 scope=team일 때만 사용합니다."


def to_task(row: TaskRow, owner: UserRow, team: TeamRow | None) -> Task:
    """DB 행을 API 응답 모델로 바꾼다. created_at은 UTC로 저장되어 있다."""
    return Task(
        id=row.id,
        title=row.title,
        description=row.description,
        status=row.status,
        priority=row.priority,
        due_date=row.due_date,
        created_at=row.created_at.replace(tzinfo=timezone.utc),
        owner=UserRef(id=owner.id, username=owner.username),
        visibility=row.visibility,
        team=TeamRef(id=team.id, name=team.name) if team is not None else None,
    )


def to_column_value(value: object) -> object:
    # Status·Priority 같은 Enum은 DB ENUM 컬럼에 맞게 문자열 값으로 저장한다.
    return value.value if isinstance(value, Enum) else value


def my_team_ids(user: User):
    return select(TeamMemberRow.team_id).where(TeamMemberRow.user_id == user.id)


def visible_to(user: User):
    """user가 볼 수 있는 할 일 조건: 내가 작성했거나, 내가 속한 팀의 TEAM 할 일.
    작성자가 없는 기존 행(owner_id NULL, PRIVATE)은 어느 쪽에도 해당하지 않아 보이지 않는다."""
    return or_(
        TaskRow.owner_id == user.id,
        and_(TaskRow.visibility == Visibility.TEAM.value, TaskRow.team_id.in_(my_team_ids(user))),
    )


def task_query():
    """할 일과 작성자, (있으면) 팀을 함께 읽는다."""
    return (
        select(TaskRow, UserRow, TeamRow)
        .join(UserRow, UserRow.id == TaskRow.owner_id)
        .outerjoin(TeamRow, TeamRow.id == TaskRow.team_id)
    )


def require_member(session: Session, team_id: int, user: User) -> None:
    if session.get(TeamMemberRow, (team_id, user.id)) is None:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=NOT_TEAM_MEMBER)


def visible_task(session: Session, task_id: int, user: User) -> TaskRow | None:
    return session.scalars(select(TaskRow).where(TaskRow.id == task_id, visible_to(user))).first()


def load_task(session: Session, row: TaskRow) -> Task:
    team = session.get(TeamRow, row.team_id) if row.team_id is not None else None
    return to_task(row, session.get(UserRow, row.owner_id), team)


class DbTaskStore:
    """MariaDB tasks 테이블에 할 일을 저장한다. 모든 작업은 로그인한 사용자 기준으로 권한을 확인한다."""

    def list(
        self,
        user: User,
        q: str | None = None,
        status: Status | None = None,
        priority: Priority | None = None,
        scope: Scope = Scope.ALL,
        team_id: int | None = None,
    ) -> list[Task]:
        """볼 수 있는 할 일 중 조건을 모두 만족하는 것을 id 순서로 반환한다. None 조건은 무시한다."""
        if scope == Scope.TEAM and team_id is None:
            raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=TEAM_ID_REQUIRED)
        if scope != Scope.TEAM and team_id is not None:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=TEAM_ID_ONLY_FOR_TEAM_SCOPE
            )
        statement = task_query().where(visible_to(user)).order_by(TaskRow.id)
        query = (q or "").strip().lower()
        if query:
            # %, _ 를 글자 그대로 검색하고, DB 정렬 규칙과 관계없이 소문자로 비교한다.
            statement = statement.where(
                func.lower(TaskRow.title).collate("utf8mb4_bin").contains(query, autoescape=True)
            )
        if status is not None:
            statement = statement.where(TaskRow.status == status.value)
        if priority is not None:
            statement = statement.where(TaskRow.priority == priority.value)
        if scope == Scope.MINE:
            statement = statement.where(TaskRow.owner_id == user.id)
        with SessionLocal() as session:
            if scope == Scope.TEAM:
                if session.get(TeamMemberRow, (team_id, user.id)) is None:
                    raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=TEAM_NOT_FOUND)
                statement = statement.where(
                    TaskRow.visibility == Visibility.TEAM.value, TaskRow.team_id == team_id
                )
            return [to_task(row, owner, team) for row, owner, team in session.execute(statement)]

    def create(self, data: TaskCreate, user: User) -> Task:
        row = TaskRow(
            title=data.title,
            description=data.description,
            status=Status.TODO.value,
            priority=data.priority.value,
            due_date=data.due_date,
            created_at=datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None),
            owner_id=user.id,
            visibility=data.visibility.value,
            team_id=data.team_id,
        )
        with SessionLocal() as session, session.begin():
            if data.team_id is not None:
                require_member(session, data.team_id, user)
            session.add(row)
            session.flush()
            return load_task(session, row)

    def update(self, task_id: int, changes: dict[str, object], user: User) -> Task | None:
        """전달된 필드만 바꾼다. 볼 수 없거나 없는 id는 None을 반환한다."""
        with SessionLocal() as session, session.begin():
            row = visible_task(session, task_id, user)
            if row is None:
                return None
            if "visibility" in changes or "team_id" in changes:
                if row.owner_id != user.id:
                    raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=OWNER_ONLY)
                visibility = changes.get("visibility", Visibility(row.visibility))
                if visibility == Visibility.PRIVATE:
                    # visibility 없이 team_id만 보냈으면 이미 TEAM인 할 일이어야 한다(PRIVATE 할 일은 거절).
                    if "visibility" not in changes:
                        raise HTTPException(
                            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=TEAM_ID_WITHOUT_TEAM
                        )
                    changes["team_id"] = None
                elif "team_id" in changes:
                    require_member(session, changes["team_id"], user)
            for name, value in changes.items():
                setattr(row, name, to_column_value(value))
            session.flush()
            return load_task(session, row)

    def delete(self, task_id: int, user: User) -> bool:
        """삭제했으면 True, 볼 수 없거나 없는 id면 False를 반환한다. 작성자가 아니면 403."""
        with SessionLocal() as session, session.begin():
            row = visible_task(session, task_id, user)
            if row is None:
                return False
            if row.owner_id != user.id:
                raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=OWNER_ONLY)
            session.delete(row)
            return True
