"""팀 생성과 멤버 관리(T18). 팀 정보는 그 팀의 멤버에게만 보이고, 볼 수 없으면 404로 응답한다."""

from datetime import timezone

from fastapi import HTTPException, status
from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import utc_now
from .database import SessionLocal
from .models import TeamMemberRow, TeamRow, UserRow
from .schemas import Member, Team, User, UserRef

TEAM_NOT_FOUND = "팀을 찾을 수 없습니다."
TEAM_NAME_TAKEN = "이미 사용 중인 팀 이름입니다."
OWNER_ONLY = "팀장만 할 수 있습니다."
USER_NOT_FOUND = "사용자를 찾을 수 없습니다."
ALREADY_MEMBER = "이미 팀 멤버입니다."
MEMBER_NOT_FOUND = "팀 멤버를 찾을 수 없습니다."
OWNER_CANNOT_LEAVE = "팀장은 팀을 떠날 수 없습니다."


def utc(value):
    return value.replace(tzinfo=timezone.utc)


def to_team(team: TeamRow, owner: UserRow) -> Team:
    return Team(
        id=team.id,
        name=team.name,
        owner=UserRef(id=owner.id, username=owner.username),
        created_at=utc(team.created_at),
    )


def to_member(member: TeamMemberRow, user: UserRow, team: TeamRow) -> Member:
    return Member(
        user=UserRef(id=user.id, username=user.username),
        is_owner=user.id == team.owner_id,
        joined_at=utc(member.created_at),
    )


def is_member(session: Session, team_id: int, user_id: int) -> bool:
    return session.get(TeamMemberRow, (team_id, user_id)) is not None


def visible_team(session: Session, team_id: int, user: User) -> TeamRow:
    """user가 멤버인 팀을 반환한다. 없거나 멤버가 아니면 404."""
    team = session.get(TeamRow, team_id)
    if team is None or not is_member(session, team_id, user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TEAM_NOT_FOUND)
    return team


class DbTeamStore:
    """teams·team_members 테이블로 팀과 멤버를 관리한다."""

    def create(self, name: str, user: User) -> Team:
        now = utc_now()
        try:
            with SessionLocal() as session, session.begin():
                team = TeamRow(name=name, owner_id=user.id, created_at=now)
                session.add(team)
                session.flush()
                # 팀장도 멤버로 저장한다.
                session.add(TeamMemberRow(team_id=team.id, user_id=user.id, created_at=now))
                session.flush()
                return to_team(team, session.get(UserRow, user.id))
        except IntegrityError:
            # teams.name UNIQUE 위반. DB 정렬 규칙상 대소문자만 다른 이름도 중복이다.
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=TEAM_NAME_TAKEN) from None

    def list_for(self, user: User) -> list[Team]:
        """user가 속한 팀을 id 순서로 반환한다."""
        statement = (
            select(TeamRow, UserRow)
            .join(TeamMemberRow, TeamMemberRow.team_id == TeamRow.id)
            .join(UserRow, UserRow.id == TeamRow.owner_id)
            .where(TeamMemberRow.user_id == user.id)
            .order_by(TeamRow.id)
        )
        with SessionLocal() as session:
            return [to_team(team, owner) for team, owner in session.execute(statement)]

    def members(self, team_id: int, user: User) -> list[Member]:
        """팀장 먼저, 이후 멤버가 된 순서로 반환한다."""
        with SessionLocal() as session:
            team = visible_team(session, team_id, user)
            statement = (
                select(TeamMemberRow, UserRow)
                .join(UserRow, UserRow.id == TeamMemberRow.user_id)
                .where(TeamMemberRow.team_id == team_id)
                .order_by(case((UserRow.id == team.owner_id, 0), else_=1), TeamMemberRow.created_at, UserRow.id)
            )
            return [to_member(member, member_user, team) for member, member_user in session.execute(statement)]

    def add_member(self, team_id: int, username: str, user: User) -> Member:
        try:
            with SessionLocal() as session, session.begin():
                team = visible_team(session, team_id, user)
                if team.owner_id != user.id:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=OWNER_ONLY)
                target = session.scalars(select(UserRow).where(UserRow.username == username)).first()
                # 아이디는 대소문자까지 정확히 같을 때만 인정한다.
                if target is None or target.username != username:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND)
                if is_member(session, team_id, target.id):
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_MEMBER)
                member = TeamMemberRow(team_id=team_id, user_id=target.id, created_at=utc_now())
                session.add(member)
                session.flush()
                return to_member(member, target, team)
        except IntegrityError:
            # 같은 멤버를 동시에 추가한 경우(team_members 기본키 위반).
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_MEMBER) from None

    def remove_member(self, team_id: int, target_user_id: int, user: User) -> None:
        """팀장은 다른 멤버를 제거하고, 멤버는 자기 자신을 지워 팀을 떠난다."""
        with SessionLocal() as session, session.begin():
            team = visible_team(session, team_id, user)
            if target_user_id != user.id and team.owner_id != user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=OWNER_ONLY)
            if target_user_id == team.owner_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=OWNER_CANNOT_LEAVE)
            member = session.get(TeamMemberRow, (team_id, target_user_id))
            if member is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MEMBER_NOT_FOUND)
            session.delete(member)


team_store = DbTeamStore()
