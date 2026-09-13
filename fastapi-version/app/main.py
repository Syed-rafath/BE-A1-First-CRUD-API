"""FastAPI implementation of the in-memory Task API assignment."""

from json import JSONDecodeError
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError, field_validator


class Task(BaseModel):
    id: int
    title: str
    done: bool = False


class CreateTaskRequest(BaseModel):
    title: str = Field(..., examples=["Buy milk"])

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = str(value).strip()
        if title == "":
            raise ValueError("title is required and cannot be empty")
        return title


class UpdateTaskRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = Field(default=None, examples=["Buy oat milk"])
    done: StrictBool | None = Field(default=None, examples=[True])

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("title cannot be empty")

        title = str(value).strip()
        if title == "":
            raise ValueError("title cannot be empty")
        return title


app = FastAPI(
    title="Task API",
    version="1.0",
    description="In-memory CRUD API for tasks.",
)


SEED_TASKS = [
    Task(id=1, title="Buy groceries", done=False),
    Task(id=2, title="Walk the dog", done=True),
    Task(id=3, title="Read a book", done=False),
]

tasks: list[Task] = [task.model_copy() for task in SEED_TASKS]
tasks_lock = Lock()


def reset_tasks() -> list[Task]:
    """Restore the task list to the seed data and return a snapshot."""
    with tasks_lock:
        tasks.clear()
        tasks.extend(task.model_copy() for task in SEED_TASKS)
        return [task.model_copy() for task in tasks]


def find_task(task_id: int) -> Task | None:
    """Return a task by id, or None when it does not exist."""
    return next((task for task in tasks if task.id == task_id), None)


def error_response(message: str, status_code: int) -> JSONResponse:
    """Return errors in the same shape as the original Express API."""
    return JSONResponse(status_code=status_code, content={"error": message})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()

    for error in errors:
        location = error.get("loc", ())
        message = str(error.get("msg", ""))

        if location[-1:] == ("done",):
            return error_response("done must be a boolean", status.HTTP_400_BAD_REQUEST)

        if location[-1:] == ("title",):
            if request.method == "POST":
                return error_response(
                    "title is required and cannot be empty",
                    status.HTTP_400_BAD_REQUEST,
                )
            return error_response("title cannot be empty", status.HTTP_400_BAD_REQUEST)

        if "Field required" in message and request.method == "POST":
            return error_response(
                "title is required and cannot be empty", status.HTTP_400_BAD_REQUEST
            )

    return error_response("invalid request", status.HTTP_400_BAD_REQUEST)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks", "/stats", "/reset"],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks", response_model=list[Task])
def list_tasks(
    done: str | None = Query(default=None, description="Filter by completion status"),
    search: str | None = Query(
        default=None, description="Filter tasks whose title contains this word"
    ),
) -> list[Task]:
    with tasks_lock:
        result = [task.model_copy() for task in tasks]

    if done is not None:
        if done not in {"true", "false"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "done must be true or false"},
            )

        is_done = done == "true"
        result = [task for task in result if task.done is is_done]

    if search is not None:
        word = search.strip()
        if word == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "search must not be empty"},
            )

        lower = word.lower()
        result = [task for task in result if lower in task.title.lower()]

    return result


@app.get("/stats")
def get_stats() -> dict[str, int]:
    with tasks_lock:
        done_count = sum(1 for task in tasks if task.done)
        total = len(tasks)

    return {
        "total": total,
        "done": done_count,
        "open": total - done_count,
    }


@app.post("/reset", response_model=list[Task])
def reset() -> list[Task]:
    return reset_tasks()


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: CreateTaskRequest) -> Task:
    with tasks_lock:
        task_id = max((task.id for task in tasks), default=0) + 1
        task = Task(id=task_id, title=payload.title, done=False)

        tasks.append(task)
        return task.model_copy()


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int) -> Task:
    with tasks_lock:
        task = find_task(task_id)

        if task is not None:
            return task.model_copy()

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": f"Task {task_id} not found"},
    )


@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, request: Request) -> Task:
    try:
        body = await request.json()
    except JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "request body must include title and/or done"},
        ) from None

    if not isinstance(body, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "request body must include title and/or done"},
        )

    has_title = "title" in body
    has_done = "done" in body

    if not has_title and not has_done:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "request body must include title and/or done"},
        )

    try:
        payload = UpdateTaskRequest.model_validate(body)
    except ValidationError as exc:
        for error in exc.errors():
            if error.get("loc", ())[-1:] == ("done",):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "done must be a boolean"},
                ) from exc

            if error.get("loc", ())[-1:] == ("title",):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "title cannot be empty"},
                ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid request"},
        ) from exc

    if has_done:
        if payload.done is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "done must be a boolean"},
            )

    with tasks_lock:
        task = find_task(task_id)

        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Task {task_id} not found"},
            )

        if has_title:
            task.title = payload.title or task.title

        if has_done:
            task.done = payload.done

        return task.model_copy()


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int) -> Response:
    with tasks_lock:
        task = find_task(task_id)

        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Task {task_id} not found"},
            )

        tasks.remove(task)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})
