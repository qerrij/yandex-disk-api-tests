"""
GET-эндпоинт раздела /v1/disk/operations/{operation_id}.

Покрываемый эндпоинт:
  GET /v1/disk/operations/{operation_id} — статус асинхронной операции

Операции запускаются через реальные async-эндпоинты
(например, POST /resources/copy непустой папки).
"""
import time

import pytest

from config import BASE_URL
from helpers import resource_exists


OPERATIONS = f"{BASE_URL}/operations"


class TestGetOperationStatus:
    """Тесты GET /v1/disk/operations/{operation_id}."""

    def test_valid_operation_returns_status(
        self, api_client, running_operation
    ):
        """Валидный operation_id → 200 с полем status."""
        response = api_client.get(
            f"{OPERATIONS}/{running_operation['id']}"
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert "status" in data
        assert data["status"] in ("in-progress", "success", "failed")

    def test_completed_operation_returns_success_status(
        self, api_client, running_operation
    ):
        """Операция доходит до статуса success."""
        deadline = time.time() + 60
        data = None
        while time.time() < deadline:
            response = api_client.get(
                f"{OPERATIONS}/{running_operation['id']}"
            )
            assert response.status_code == 200, response.text
            data = response.json()
            if data["status"] == "success":
                break
            if data["status"] == "failed":
                pytest.fail(f"Операция завершилась с ошибкой: {data}")
            time.sleep(1)

        assert data and data["status"] == "success", \
            f"Операция не завершилась за 60 сек: {data}"

    def test_successful_operation_created_target_resource(
        self, api_client, running_operation
    ):
        """E2E: после success ресурс реально существует по целевому пути."""
        deadline = time.time() + 60
        data = None
        while time.time() < deadline:
            response = api_client.get(
                f"{OPERATIONS}/{running_operation['id']}"
            )
            data = response.json()
            if data["status"] in ("success", "failed"):
                break
            time.sleep(1)

        assert data["status"] == "success", \
            f"Операция не завершилась успехом: {data}"

        assert resource_exists(api_client, running_operation["dst"]), \
            f"Копия не появилась по пути {running_operation['dst']}"

    def test_malformed_operation_id_returns_404(self, api_client):
        """Невалидный/несуществующий operation_id → 404 с телом ошибки."""
        response = api_client.get(f"{OPERATIONS}/not-a-valid-id")
        assert response.status_code == 404, response.text
        assert "error" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])