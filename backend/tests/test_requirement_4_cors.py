import pytest
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_cors_preflight_production_vercel_origin():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://quali-forge-app.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://quali-forge-app.vercel.app"
    assert "GET" in response.headers.get("access-control-allow-methods", "")
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_cors_preflight_custom_origin_qualiforge_vercel():
    response = client.options(
        "/api/batches",
        headers={
            "Origin": "https://qualiforge-app.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://qualiforge-app.vercel.app"

def test_cors_get_production_origin():
    response = client.get(
        "/api/health",
        headers={
            "Origin": "https://quali-forge-app.vercel.app",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://quali-forge-app.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_cors_investigation_endpoint():
    response = client.options(
        "/api/investigation/run",
        headers={
            "Origin": "https://quali-forge-app.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://quali-forge-app.vercel.app"

def test_untrusted_origin_disallowed():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://malicious-site.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") != "https://malicious-site.example.com"
