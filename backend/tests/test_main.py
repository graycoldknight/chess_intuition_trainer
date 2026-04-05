"""
Phase 1 RED: Test health check endpoint.
"""


def test_health_check_returns_200(test_client):
    """GET / returns 200 with status ok."""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "chess-intuition-trainer"
