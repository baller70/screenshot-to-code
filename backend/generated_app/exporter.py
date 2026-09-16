# pyright: reportUnknownVariableType=false
import json
import re
from io import BytesIO
from typing import Literal
from zipfile import ZIP_DEFLATED, ZipFile

from generated_app.manifest import BackendContract, analyze_generated_app_html
from generated_app.repair import build_quality_gates, build_repair_prompt


BackendAdapter = Literal["fixture", "sqlite", "postgres", "webhook"]


def slugify_app_name(app_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", app_name.strip().lower()).strip("-")
    return slug or "generated-app"


def _python_string(value: str) -> str:
    return repr(value)


def _endpoint_function_name(contract: BackendContract) -> str:
    route_part = contract.api_route.strip("/").replace("/", "_").replace("-", "_")
    name = re.sub(r"[^A-Za-z0-9_]+", "_", route_part).strip("_")
    if not name:
        name = contract.contract_id.replace("-", "_")
    if name[0].isdigit():
        name = f"endpoint_{name}"
    return name


def _build_fixture_backend_main(contracts: list[BackendContract]) -> str:
    lines = [
        "from fastapi import FastAPI",
        "from pydantic import BaseModel",
        "",
        "app = FastAPI(title='Generated App Backend')",
        "submissions: list[dict] = []",
        "",
        "",
        "class Submission(BaseModel):",
        "    data: dict = {}",
        "",
        "",
        "@app.get('/api/health')",
        "def health():",
        "    return {'ok': True}",
        "",
        "",
        "@app.get('/api/fixtures')",
        "def fixtures():",
        "    return {'submissions': submissions}",
        "",
    ]
    for contract in contracts:
        route = _python_string(contract.api_route)
        function_name = _endpoint_function_name(contract)
        lines.extend(
            [
                "",
                f"@app.{contract.method.lower()}({route})",
                f"def {function_name}(submission: Submission):",
                "    record = submission.data",
                "    submissions.append(record)",
                "    return {'ok': True, 'record': record}",
            ]
        )
    return "\n".join(lines) + "\n"


def _build_sqlite_backend_main(contracts: list[BackendContract]) -> str:
    lines = [
        "import json",
        "import sqlite3",
        "from fastapi import FastAPI",
        "from pydantic import BaseModel",
        "",
        "DB_PATH = 'generated_app.db'",
        "app = FastAPI(title='Generated App Backend')",
        "",
        "",
        "class Submission(BaseModel):",
        "    data: dict = {}",
        "",
        "",
        "def init_db():",
        "    with sqlite3.connect(DB_PATH) as connection:",
        "        connection.execute('CREATE TABLE IF NOT EXISTS generated_submission (id INTEGER PRIMARY KEY AUTOINCREMENT, contract_id TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')",
        "",
        "",
        "def save_submission(contract_id: str, payload: dict):",
        "    init_db()",
        "    with sqlite3.connect(DB_PATH) as connection:",
        "        connection.execute('INSERT INTO generated_submission (contract_id, payload_json) VALUES (?, ?)', (contract_id, json.dumps(payload)))",
        "    return payload",
        "",
        "",
        "@app.get('/api/health')",
        "def health():",
        "    init_db()",
        "    return {'ok': True}",
    ]
    for contract in contracts:
        route = _python_string(contract.api_route)
        function_name = _endpoint_function_name(contract)
        lines.extend(
            [
                "",
                f"@app.{contract.method.lower()}({route})",
                f"def {function_name}(submission: Submission):",
                f"    record = save_submission({contract.contract_id!r}, submission.data)",
                "    return {'ok': True, 'record': record}",
            ]
        )
    return "\n".join(lines) + "\n"


def _build_postgres_backend_main(contracts: list[BackendContract]) -> str:
    lines = [
        "import os",
        "from fastapi import FastAPI",
        "from pydantic import BaseModel",
        "",
        "DATABASE_URL = os.getenv('DATABASE_URL')",
        "app = FastAPI(title='Generated App Backend')",
        "",
        "",
        "class Submission(BaseModel):",
        "    data: dict = {}",
        "",
        "",
        "@app.get('/api/health')",
        "def health():",
        "    return {'ok': True, 'databaseConfigured': bool(DATABASE_URL)}",
        "",
        "",
        "def save_submission(contract_id: str, payload: dict):",
        "    # Postgres adapter placeholder: connect your preferred driver here.",
        "    # The generated contract_id and payload shape are stable.",
        "    return {'contractId': contract_id, 'payload': payload, 'databaseUrlConfigured': bool(DATABASE_URL)}",
    ]
    for contract in contracts:
        route = _python_string(contract.api_route)
        function_name = _endpoint_function_name(contract)
        lines.extend(
            [
                "",
                f"@app.{contract.method.lower()}({route})",
                f"def {function_name}(submission: Submission):",
                f"    record = save_submission({contract.contract_id!r}, submission.data)",
                "    return {'ok': True, 'record': record}",
            ]
        )
    return "\n".join(lines) + "\n"


def _build_webhook_backend_main(contracts: list[BackendContract]) -> str:
    lines = [
        "import os",
        "import httpx",
        "from fastapi import FastAPI",
        "from pydantic import BaseModel",
        "",
        "WEBHOOK_URL = os.getenv('WEBHOOK_URL')",
        "app = FastAPI(title='Generated App Backend')",
        "",
        "",
        "class Submission(BaseModel):",
        "    data: dict = {}",
        "",
        "",
        "@app.get('/api/health')",
        "def health():",
        "    return {'ok': True, 'webhookConfigured': bool(WEBHOOK_URL)}",
        "",
        "",
        "def forward_submission(contract_id: str, payload: dict):",
        "    if not WEBHOOK_URL:",
        "        return {'forwarded': False, 'reason': 'WEBHOOK_URL is not configured', 'payload': payload}",
        "    response = httpx.post(WEBHOOK_URL, json={'contractId': contract_id, 'payload': payload}, timeout=10)",
        "    return {'forwarded': response.is_success, 'statusCode': response.status_code, 'payload': payload}",
    ]
    for contract in contracts:
        route = _python_string(contract.api_route)
        function_name = _endpoint_function_name(contract)
        lines.extend(
            [
                "",
                f"@app.{contract.method.lower()}({route})",
                f"def {function_name}(submission: Submission):",
                f"    record = forward_submission({contract.contract_id!r}, submission.data)",
                "    return {'ok': True, 'record': record}",
            ]
        )
    return "\n".join(lines) + "\n"


def _build_backend_main(
    contracts: list[BackendContract],
    backend_adapter: BackendAdapter,
) -> str:
    if backend_adapter == "sqlite":
        return _build_sqlite_backend_main(contracts)
    if backend_adapter == "postgres":
        return _build_postgres_backend_main(contracts)
    if backend_adapter == "webhook":
        return _build_webhook_backend_main(contracts)
    return _build_fixture_backend_main(contracts)


def _build_schema_sql(contracts: list[BackendContract]) -> str:
    statements = [
        "CREATE TABLE IF NOT EXISTS generated_submission (",
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,",
        "  contract_id TEXT NOT NULL,",
        "  payload_json TEXT NOT NULL,",
        "  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ");",
    ]
    for contract in contracts:
        table_name = re.sub(r"[^a-z0-9_]+", "_", contract.contract_id.lower()).strip("_")
        if table_name.startswith("form"):
            table_name = "evaluation"
        statements.extend(
            [
                "",
                f"CREATE TABLE IF NOT EXISTS {table_name} (",
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,",
                "  payload_json TEXT NOT NULL,",
                "  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
                ");",
            ]
        )
    return "\n".join(statements) + "\n"


def _build_smoke_test(contracts: list[BackendContract]) -> str:
    first_route = contracts[0].api_route if contracts else "/api/health"
    return f"""from fastapi.testclient import TestClient

from backend.main import app


def test_health():
    client = TestClient(app)
    assert client.get('/api/health').json() == {{'ok': True}}


def test_fixture_backed_submission():
    client = TestClient(app)
    response = client.post({first_route!r}, json={{'data': {{'athleteName': 'Jordan'}}}})
    assert response.status_code == 200
    assert response.json()['ok'] is True
"""


def _build_readme(app_name: str, backend_adapter: BackendAdapter) -> str:
    return f"""# {app_name}

Generated by Screenshot-to-Code Factory mirror mode.

Backend adapter: {backend_adapter}

## Run the backend

```bash
cd backend
pip install fastapi uvicorn pytest httpx
uvicorn main:app --reload
```

## Run smoke tests

```bash
pytest backend/tests/test_smoke.py
```

Endpoints are generated from visible forms and action contracts in the mirrored website.
"""


def build_generated_app_export(
    code: str,
    app_name: str = "generated-app",
    backend_adapter: BackendAdapter = "fixture",
) -> bytes:
    slug = slugify_app_name(app_name)
    manifest = analyze_generated_app_html(code)
    gates = build_quality_gates(manifest)
    fixtures = {
        "routes": [route.model_dump(by_alias=True) for route in manifest.routes],
        "assets": [asset.model_dump(by_alias=True) for asset in manifest.assets],
        "submissions": [],
    }

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(f"{slug}/frontend/index.html", code)
        archive.writestr(
            f"{slug}/backend/main.py",
            _build_backend_main(manifest.backend_contracts, backend_adapter),
        )
        archive.writestr(f"{slug}/backend/fixtures.json", json.dumps(fixtures, indent=2))
        archive.writestr(f"{slug}/backend/schema.sql", _build_schema_sql(manifest.backend_contracts))
        archive.writestr(f"{slug}/backend/tests/test_smoke.py", _build_smoke_test(manifest.backend_contracts))
        archive.writestr(f"{slug}/manifest.json", json.dumps(manifest.model_dump(by_alias=True), indent=2))
        archive.writestr(
            f"{slug}/quality-gates.json",
            json.dumps([gate.model_dump(by_alias=True) for gate in gates], indent=2),
        )
        archive.writestr(
            f"{slug}/repair-prompt.md",
            build_repair_prompt(manifest, gates),
        )
        archive.writestr(f"{slug}/README.md", _build_readme(app_name, backend_adapter))
    return output.getvalue()
