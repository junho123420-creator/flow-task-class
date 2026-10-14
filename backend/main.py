import logging

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .auth import (
    LOGIN_FAILED,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    USERNAME_TAKEN,
    auth_store,
    current_user,
)
from .schemas import (
    LoginRequest,
    Member,
    MemberAdd,
    Priority,
    Scope,
    SignupRequest,
    Status,
    Task,
    TaskCreate,
    TaskUpdate,
    Team,
    TeamCreate,
    User,
)
from .store import DbTaskStore
from .teams import team_store

app = FastAPI(title="Task Flow API")
store = DbTaskStore()
logger = logging.getLogger(__name__)

TASK_NOT_FOUND = "할 일을 찾을 수 없습니다."
DATABASE_ERROR = "DB에 연결할 수 없거나 처리 중 오류가 발생했습니다."


@app.exception_handler(SQLAlchemyError)
def handle_database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
    """DB 오류는 내부 내용을 응답에 노출하지 않고 503으로 알린다. 자세한 내용은 서버 로그에 남긴다."""
    logger.error("DB 오류: %s %s: %s", request.method, request.url.path, error)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": DATABASE_ERROR})


@app.get("/api/health")
def health() -> dict[str, str]:
    """API 서버가 요청을 처리할 수 있는지 확인한다."""
    return {"status": "ok"}


@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest) -> User:
    """회원가입만 하고 로그인하지 않는다(세션 쿠키 없음)."""
    user = auth_store.signup(data.username, data.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=USERNAME_TAKEN)
    return user


@app.post("/api/auth/login")
def login(data: LoginRequest, response: Response) -> User:
    """로그인하고 세션 쿠키를 보낸다. 없는 아이디와 틀린 비밀번호는 같은 401로 응답한다."""
    result = auth_store.login(data.username, data.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=LOGIN_FAILED)
    user, token = result
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_MAX_AGE, path="/", httponly=True, samesite="lax"
    )
    return user


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> None:
    """현재 세션을 지우고 쿠키를 삭제한다. 로그인하지 않았어도 204."""
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        auth_store.logout(token)
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)) -> User:
    """로그인한 사용자를 반환한다."""
    return user


@app.post("/api/teams", status_code=status.HTTP_201_CREATED)
def create_team(data: TeamCreate, user: User = Depends(current_user)) -> Team:
    """팀을 만든다. 만든 사람이 팀장이 되고 멤버로도 저장된다."""
    return team_store.create(data.name, user)


@app.get("/api/teams")
def list_teams(user: User = Depends(current_user)) -> list[Team]:
    """내가 속한 팀 목록을 id 순서로 반환한다."""
    return team_store.list_for(user)


@app.get("/api/teams/{team_id}/members")
def list_members(team_id: int, user: User = Depends(current_user)) -> list[Member]:
    """팀 멤버 목록. 그 팀의 멤버만 볼 수 있다."""
    return team_store.members(team_id, user)


@app.post("/api/teams/{team_id}/members", status_code=status.HTTP_201_CREATED)
def add_member(team_id: int, data: MemberAdd, user: User = Depends(current_user)) -> Member:
    """팀장이 아이디로 멤버를 추가한다."""
    return team_store.add_member(team_id, data.username, user)


@app.delete("/api/teams/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(team_id: int, user_id: int, user: User = Depends(current_user)) -> None:
    """팀장의 멤버 제거 또는 본인 탈퇴."""
    team_store.remove_member(team_id, user_id, user)


@app.get("/api/tasks")
def list_tasks(
    q: str | None = None,
    status: Status | None = None,
    priority: Priority | None = None,
    scope: Scope = Scope.ALL,
    team_id: int | None = None,
    user: User = Depends(current_user),
) -> list[Task]:
    """볼 수 있는 할 일에 제목 검색(q), 상태·우선순위·범위 필터를 AND로 적용해 등록 순서로 반환한다."""
    return store.list(user, q=q, status=status, priority=priority, scope=scope, team_id=team_id)


@app.post("/api/tasks", status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, user: User = Depends(current_user)) -> Task:
    """할 일을 등록한다. 작성자는 로그인 사용자이고 상태는 항상 TODO로 시작한다."""
    return store.create(data, user)


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, data: TaskUpdate, user: User = Depends(current_user)) -> Task:
    """보낸 필드만 수정하고 나머지는 유지한다. 공개 범위·팀은 작성자만 바꾼다."""
    task = store.update(task_id, data.changes(), user)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND)
    return task


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, user: User = Depends(current_user)) -> None:
    """할 일을 삭제한다. 작성자만 삭제할 수 있다."""
    if not store.delete(task_id, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND)
