def test_api_responses_carry_baseline_security_headers(client):
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" in response.headers
    assert "Permissions-Policy" in response.headers
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )


def test_docs_page_is_excluded_from_the_strict_csp_so_swagger_ui_still_loads(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
    # Other headers still apply even on the docs route.
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_error_responses_also_carry_security_headers(client):
    response = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.headers["X-Content-Type-Options"] == "nosniff"
