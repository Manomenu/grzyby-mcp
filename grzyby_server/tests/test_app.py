from fastapi.testclient import TestClient


def test_health_answers_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_routes_carry_no_api_prefix(client: TestClient) -> None:
    # /api is stripped at the edge (vite proxy, nginx). A route declared with it would be
    # reachable in no environment at all.
    assert client.get("/api/health").status_code == 404
