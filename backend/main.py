import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .schemas import Priority, Status, Task, TaskCreate, TaskUpdate
from .store import DbTaskStore

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


@app.get("/api/tasks")
def list_tasks(
    q: str | None = None,
    status: Status | None = None,
    priority: Priority | None = None,
) -> list[Task]:
    """제목 검색(q)과 상태·우선순위 필터를 AND로 적용해 등록 순서로 반환한다."""
    return store.list(q=q, status=status, priority=priority)


@app.post("/api/tasks", status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate) -> Task:
    """할 일을 등록한다. 상태는 항상 TODO로 시작한다."""
    return store.create(data)


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, data: TaskUpdate) -> Task:
    """보낸 필드만 수정하고 나머지는 유지한다."""
    task = store.update(task_id, data.changes())
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND)
    return task


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int) -> None:
    """할 일을 삭제한다."""
    if not store.delete(task_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND)
