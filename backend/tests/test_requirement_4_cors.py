import pytest
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_cors_preflight_production_vercel_origin():
    """OPTIONS request with production Origin: https://quali-forge-app.vercel.app must receive 200 and proper headers."""
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
    """OPTIONS request with Origin: https://qualiforge-app.vercel.app must also be allowed."""
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
    """GET request with production origin must return proper Access-Control-Allow-Origin header."""
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
    """Investigation endpoints must support CORS for production origin."""
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
    """Untrusted origins should not receive Access-Control-Allow-Origin matching their origin."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://malicious-site.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # When CORS rejects an origin, starlette either does not return access-control-allow-origin or rejects
    assert response.headers.get("access-control-allow-origin") != "https://malicious-site.example.com"
