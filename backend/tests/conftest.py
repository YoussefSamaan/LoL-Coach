from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
import backend.routes.recommend as recommend_routes
import backend.routes.router as router_routes


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """
    Creates a fresh FastAPI app and TestClient for each test.
    This avoids shared state between tests.
    """
    recommend_routes._service_instance = None
    router_routes._registry_instance = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    recommend_routes._service_instance = None
    router_routes._registry_instance = None
