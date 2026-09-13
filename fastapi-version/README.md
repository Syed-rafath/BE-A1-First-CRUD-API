# Task API - FastAPI Version

A Python/FastAPI implementation of the Flyrank Backend Engineering Assignment 1 CRUD API.

This version mirrors the original Express API:

- In-memory task storage
- Create, read, update, and delete tasks
- Optional filtering by completion status
- Case-insensitive title search
- Task statistics
- Reset endpoint for demos and tests
- Interactive Swagger docs

## Requirements

- Python 3.10+

## Getting Started

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the server:

```bash
uvicorn app.main:app --reload --port 8000
```

The API runs at `http://localhost:8000`.

Interactive API docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Endpoints

### `GET /`

Returns metadata about the API.

```json
{
  "name": "Task API",
  "version": "1.0",
  "endpoints": ["/tasks", "/stats", "/reset"]
}
```

### `GET /health`

Health check endpoint.

```json
{ "status": "ok" }
```

### `GET /tasks`

Returns all tasks. Optional query parameters can filter the list.

| Query | Example | Effect |
|-------|---------|--------|
| `done` | `?done=true` | Only finished tasks |
| `done` | `?done=false` | Only open tasks |
| `search` | `?search=milk` | Title contains the word, case-insensitive |

Filters can be combined:

```bash
curl "http://localhost:8000/tasks?done=false&search=book"
```

### `GET /stats`

Returns computed counts for the current task list.

```json
{ "total": 3, "done": 1, "open": 2 }
```

### `POST /reset`

Restores the three seed example tasks.

```bash
curl -X POST http://localhost:8000/reset
```

### `GET /tasks/{id}`

Returns a single task by id.

```bash
curl http://localhost:8000/tasks/1
```

### `POST /tasks`

Creates a new task.

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'
```

### `PUT /tasks/{id}`

Updates a task's `title` and/or `done`.

```bash
curl -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"done": true}'
```

### `DELETE /tasks/{id}`

Deletes a task.

```bash
curl -X DELETE http://localhost:8000/tasks/1
```

## Run Tests

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
pytest
```
