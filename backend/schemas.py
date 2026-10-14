import re
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TITLE_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 2000
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class Status(str, Enum):
    TODO = "TODO"
    DOING = "DOING"
    DONE = "DONE"


class Priority(str, Enum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


def check_due_date_format(value: object) -> object:
    # "YYYY-MM-DD" 문자열만 허용하고 숫자·일시 문자열은 날짜로 변환하지 않는다.
    # 실제 존재하는 날짜인지는 이후 date 변환에서 확인한다.
    if value is None:
        return None
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise ValueError("마감일은 YYYY-MM-DD 형식이어야 합니다.")
    return value


def check_title(value: str | None) -> str | None:
    if value is None:
        return None
    title = value.strip()
    if not 1 <= len(title) <= TITLE_MAX_LENGTH:
        raise ValueError(f"제목은 앞뒤 공백 제거 후 1~{TITLE_MAX_LENGTH}자여야 합니다.")
    return title


class TaskCreate(BaseModel):
    """POST /api/tasks 요청 본문. 정의되지 않은 필드는 거절한다."""

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str = Field(default="", max_length=DESCRIPTION_MAX_LENGTH)
    priority: Priority = Priority.NORMAL
    due_date: date | None = None

    _check_due_date = field_validator("due_date", mode="before")(check_due_date_format)
    _check_title = field_validator("title")(check_title)


class TaskUpdate(BaseModel):
    """PATCH /api/tasks/{id} 요청 본문. 보낸 필드만 수정한다."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: Status | None = None
    priority: Priority | None = None
    # null을 보내면 마감일을 지운다.
    due_date: date | None = None

    _check_due_date = field_validator("due_date", mode="before")(check_due_date_format)
    _check_title = field_validator("title")(check_title)

    @model_validator(mode="after")
    def reject_null(self) -> "TaskUpdate":
        # 생략은 허용하지만 due_date 외의 필드에 null을 보내면 거절한다.
        for name in ("title", "description", "status", "priority"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name}에는 null을 보낼 수 없습니다.")
        return self

    def changes(self) -> dict[str, object]:
        """요청에 실제로 포함된 필드만 반환한다."""
        return self.model_dump(exclude_unset=True)


class Task(BaseModel):
    """API 응답의 할 일."""

    id: int
    title: str
    description: str
    status: Status
    priority: Priority
    due_date: date | None
    created_at: datetime


USERNAME_PATTERN = re.compile(r"[a-z0-9_]{3,30}")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


class SignupRequest(BaseModel):
    """POST /api/auth/signup 요청 본문. 아이디는 변환하지 않고 형식만 확인한다."""

    model_config = ConfigDict(extra="forbid")

    username: str
    password: str

    @field_validator("username")
    @classmethod
    def check_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("아이디는 영문 소문자·숫자·밑줄 3~30자여야 합니다.")
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        # 비밀번호는 앞뒤 공백을 지우지 않고 그대로 쓴다.
        if not PASSWORD_MIN_LENGTH <= len(value) <= PASSWORD_MAX_LENGTH:
            raise ValueError(f"비밀번호는 {PASSWORD_MIN_LENGTH}~{PASSWORD_MAX_LENGTH}자여야 합니다.")
        return value


class LoginRequest(BaseModel):
    """POST /api/auth/login 요청 본문. 형식이 달라도 422가 아닌 401로 처리하도록 길이만 제한한다."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(max_length=100)
    password: str = Field(max_length=1000)


class User(BaseModel):
    """API 응답의 사용자. 비밀번호 해시는 포함하지 않는다."""

    id: int
    username: str
    created_at: datetime


TEAM_NAME_MAX_LENGTH = 50


class TeamCreate(BaseModel):
    """POST /api/teams 요청 본문."""

    model_config = ConfigDict(extra="forbid")

    name: str

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        name = value.strip()
        if not 1 <= len(name) <= TEAM_NAME_MAX_LENGTH:
            raise ValueError(f"팀 이름은 앞뒤 공백 제거 후 1~{TEAM_NAME_MAX_LENGTH}자여야 합니다.")
        return name


class MemberAdd(BaseModel):
    """POST /api/teams/{team_id}/members 요청 본문."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(max_length=100)


class UserRef(BaseModel):
    """다른 객체 안에 넣는 사용자 요약."""

    id: int
    username: str


class Team(BaseModel):
    """API 응답의 팀."""

    id: int
    name: str
    owner: UserRef
    created_at: datetime


class Member(BaseModel):
    """API 응답의 팀 멤버."""

    user: UserRef
    is_owner: bool
    joined_at: datetime
