from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def setup_function() -> None:
    client.post("/reset")


def test_root_metadata() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks", "/stats", "/reset"],
    }


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_tasks() -> None:
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "title": "Buy groceries", "done": False},
        {"id": 2, "title": "Walk the dog", "done": True},
        {"id": 3, "title": "Read a book", "done": False},
    ]


def test_filter_tasks_by_done() -> None:
    response = client.get("/tasks?done=true")

    assert response.status_code == 200
    assert response.json() == [{"id": 2, "title": "Walk the dog", "done": True}]


def test_search_tasks_by_title() -> None:
    response = client.get("/tasks?search=book")

    assert response.status_code == 200
    assert response.json() == [{"id": 3, "title": "Read a book", "done": False}]


def test_empty_search_returns_400() -> None:
    response = client.get("/tasks?search=   ")

    assert response.status_code == 400
    assert response.json() == {"error": "search must not be empty"}


def test_invalid_done_filter_returns_400() -> None:
    response = client.get("/tasks?done=yes")

    assert response.status_code == 400
    assert response.json() == {"error": "done must be true or false"}


def test_stats() -> None:
    response = client.get("/stats")

    assert response.status_code == 200
    assert response.json() == {"total": 3, "done": 1, "open": 2}


def test_create_task() -> None:
    response = client.post("/tasks", json={"title": " Buy milk "})

    assert response.status_code == 201
    assert response.json() == {"id": 4, "title": "Buy milk", "done": False}


def test_create_task_requires_title() -> None:
    response = client.post("/tasks", json={"title": "   "})

    assert response.status_code == 400
    assert response.json() == {"error": "title is required and cannot be empty"}


def test_concurrent_task_creation_keeps_unique_ids() -> None:
    def create_task(index: int) -> dict:
        response = client.post("/tasks", json={"title": f"Task {index}"})
        assert response.status_code == 201
        return response.json()

    with ThreadPoolExecutor(max_workers=10) as executor:
        created_tasks = list(executor.map(create_task, range(10)))

    created_ids = [task["id"] for task in created_tasks]
    all_ids = [task["id"] for task in client.get("/tasks").json()]

    assert len(created_ids) == len(set(created_ids))
    assert len(all_ids) == len(set(all_ids))
    assert len(all_ids) == 13


def test_get_task() -> None:
    response = client.get("/tasks/1")

    assert response.status_code == 200
    assert response.json() == {"id": 1, "title": "Buy groceries", "done": False}


def test_get_missing_task_returns_404() -> None:
    response = client.get("/tasks/99")

    assert response.status_code == 404
    assert response.json() == {"error": "Task 99 not found"}


def test_update_task() -> None:
    response = client.put("/tasks/1", json={"title": "Buy oat milk", "done": True})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "title": "Buy oat milk", "done": True}


def test_update_task_accepts_partial_payload() -> None:
    response = client.put("/tasks/1", json={"done": True})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "title": "Buy groceries", "done": True}


def test_update_task_requires_title_or_done() -> None:
    response = client.put("/tasks/1", json={})

    assert response.status_code == 400
    assert response.json() == {"error": "request body must include title and/or done"}


def test_update_task_requires_json_body() -> None:
    response = client.put("/tasks/1")

    assert response.status_code == 400
    assert response.json() == {"error": "request body must include title and/or done"}


def test_update_task_validates_done_boolean() -> None:
    response = client.put("/tasks/1", json={"done": "yes"})

    assert response.status_code == 400
    assert response.json() == {"error": "done must be a boolean"}


def test_update_task_rejects_null_done() -> None:
    response = client.put("/tasks/1", json={"done": None})

    assert response.status_code == 400
    assert response.json() == {"error": "done must be a boolean"}


def test_delete_task() -> None:
    response = client.delete("/tasks/1")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/tasks/1").json() == {"error": "Task 1 not found"}


def test_reset_tasks() -> None:
    client.post("/tasks", json={"title": "Temporary task"})

    response = client.post("/reset")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "title": "Buy groceries", "done": False},
        {"id": 2, "title": "Walk the dog", "done": True},
        {"id": 3, "title": "Read a book", "done": False},
    ]
