import uuid

from app.core.config import get_settings


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def test_register_creates_account_and_sets_session_cookie(client):
    email = _unique_email()
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correcthorse1", "display_name": "Whisker Fan"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email
    assert body["display_name"] == "Whisker Fan"
    assert body["avatar_url"] is None
    assert "id" in body
    assert "password" not in body
    assert "password_hash" not in body
    assert get_settings().session_cookie_name in response.cookies


def test_register_rejects_duplicate_email(client):
    email = _unique_email()
    first = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correcthorse1", "display_name": "First"},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "differentpass2", "display_name": "Second"},
    )
    assert second.status_code == 409


def test_register_is_case_insensitive_on_email(client):
    email = _unique_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correcthorse1", "display_name": "Original"},
    )
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email.upper(), "password": "correcthorse1", "display_name": "Duplicate"},
    )
    assert response.status_code == 409


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email(), "password": "short1", "display_name": "Tester"},
    )
    assert response.status_code == 422


def test_register_rejects_password_without_a_digit(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email(), "password": "alllettersnodigits", "display_name": "Tester"},
    )
    assert response.status_code == 422


def test_register_rejects_missing_fields(client):
    response = client.post("/api/v1/auth/register", json={"email": _unique_email()})
    assert response.status_code == 422


def test_register_rejects_invalid_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "correcthorse1", "display_name": "Tester"},
    )
    assert response.status_code == 422


def test_login_with_correct_credentials(client):
    email = _unique_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correcthorse1", "display_name": "Login Tester"},
    )
    # Fresh client-side state is simulated by just calling login again —
    # TestClient's cookie jar already carries the session, but login must
    # independently succeed with the right credentials regardless.
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correcthorse1"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_login_with_wrong_password_is_rejected(client):
    email = _unique_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correcthorse1", "display_name": "Tester"},
    )
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpass1"})
    assert response.status_code == 401


def test_login_with_nonexistent_email_gives_identical_error_to_wrong_password(client):
    wrong_password_response = client.post(
        "/api/v1/auth/login", json={"email": _unique_email(), "password": "whatever1"}
    )
    # Register a real user, then get the wrong-password response for comparison.
    email = _unique_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correcthorse1", "display_name": "Tester"},
    )
    real_user_wrong_password = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrongpass1"}
    )

    assert wrong_password_response.status_code == real_user_wrong_password.status_code == 401
    assert wrong_password_response.json()["detail"] == real_user_wrong_password.json()["detail"]


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_when_authenticated(client, register_user):
    user = register_user(display_name="Me Tester")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert response.json()["display_name"] == "Me Tester"


def test_logout_clears_session(client, register_user):
    register_user()
    assert client.get("/api/v1/auth/me").status_code == 200

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    assert client.get("/api/v1/auth/me").status_code == 401


def test_invalid_session_cookie_is_rejected(client):
    client.cookies.set(get_settings().session_cookie_name, "not-a-real-token")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_update_me_changes_display_name(client, register_user):
    register_user(display_name="Old Name")
    response = client.patch("/api/v1/auth/me", json={"display_name": "New Name"})
    assert response.status_code == 200
    assert response.json()["display_name"] == "New Name"


def test_auth_endpoints_are_rate_limited(client, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    try:
        responses = [
            client.post(
                "/api/v1/auth/login",
                json={"email": _unique_email(), "password": "whatever123"},
            )
            for _ in range(4)
        ]
        assert 429 in [r.status_code for r in responses]
    finally:
        get_settings.cache_clear()
