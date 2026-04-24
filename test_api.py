"""
Production-grade tests for AIVisoor backend.
Run: poetry run pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from main import app
from database import Base, get_db
from config import settings

# ── Test DB setup ─────────────────────────────────────────────────────────────

TEST_DB_URL = settings.DATABASE_URL.replace("/aivisoor", "/aivisoor_test")

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, email="test@example.com", password="TestPass1"):
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "Test User"
    })
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


# ── Auth tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "TestPass1",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["full_name"] == "New User"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "TestPass1", "full_name": "User"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "weak@example.com", "password": "weak", "full_name": "User"
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "password": "TestPass1", "full_name": "User"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com", "password": "TestPass1"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "wrongpw@example.com", "password": "TestPass1", "full_name": "User"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrongpw@example.com", "password": "WrongPass1"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    token = await register_and_login(client, "me@example.com")
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    token = await register_and_login(client, "update@example.com")
    resp = await client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Updated Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"


# ── Projects tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    token = await register_and_login(client, "proj@example.com")
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "domain": "test.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Test Project"


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient):
    token = await register_and_login(client, "projlist@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(3):
        await client.post("/api/v1/projects", json={"name": f"Project {i}"}, headers=headers)
    resp = await client.get("/api/v1/projects", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient):
    token = await register_and_login(client, "projdel@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    proj = await client.post("/api/v1/projects", json={"name": "To Delete"}, headers=headers)
    pid = proj.json()["id"]
    del_resp = await client.delete(f"/api/v1/projects/{pid}", headers=headers)
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/api/v1/projects/{pid}", headers=headers)
    assert get_resp.status_code == 404


# ── Reports tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_report(client: AsyncClient):
    token = await register_and_login(client, "report@example.com")
    resp = await client.post(
        "/api/v1/reports",
        json={"domain": "example.com", "niche": "software"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["domain"] == "example.com"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_reports(client: AsyncClient):
    token = await register_and_login(client, "replist@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/api/v1/reports", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_report_isolation(client: AsyncClient):
    """User A cannot access User B's report."""
    token_a = await register_and_login(client, "usera@example.com")
    token_b = await register_and_login(client, "userb@example.com")
    report = await client.post(
        "/api/v1/reports",
        json={"domain": "a-only.com"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    report_id = report.json()["id"]
    resp = await client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


# ── Subscription tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_plans(client: AsyncClient):
    resp = await client.get("/api/v1/subscriptions/plans")
    assert resp.status_code == 200
    data = resp.json()["plans"]
    assert "free" in data
    assert "starter" in data
    assert "pro" in data
    assert "agency" in data


@pytest.mark.asyncio
async def test_get_subscription(client: AsyncClient):
    token = await register_and_login(client, "sub@example.com")
    resp = await client.get(
        "/api/v1/subscriptions/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] in ("free", "starter", "pro", "agency")


# ── Health check ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
