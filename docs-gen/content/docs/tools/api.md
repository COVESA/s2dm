---
title: REST API
weight: 115
chapter: false
---

## REST API

The S2DM REST API is implemented using `FastAPI` and exposes HTTP endpoints for validating GraphQL schemas and queries, filtering schemas, and exporting models into different formats. It is documented through the Swagger UI at `/api/v1/docs` and the OpenAPI capabilities endpoint at `/api/v1/capabilities`.

### Run locally

```bash
uv run uvicorn s2dm.api.main:app --reload --host 127.0.0.1 --port 8000
```

When running locally, the API is available at `http://127.0.0.1:8000`, including Swagger UI at `http://127.0.0.1:8000/api/v1/docs` and the machine-readable, JSON-formatted capabilities endpoint at `http://127.0.0.1:8000/api/v1/capabilities`.

> Alternatively, a more modern API documentation can be viewed at `http://127.0.0.1:8000/api/v1/redoc`.
