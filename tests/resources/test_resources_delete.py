"""
DELETE-эндпоинт раздела /v1/disk/resources.

Покрываемый эндпоинт:
  DELETE /v1/disk/resources — удаление файла или папки
"""
import pytest

from config import BASE_URL
from helpers  import wait_for_operation, resource_exists


class TestDeleteResource:
    """Тесты DELETE /v1/disk/resources — удаление файла или папки."""

    def test_delete_file_returns_204_and_removes_resource(
        self, api_client, test_file_in_folder
    ):
        """Удаление файла → 204 No Content, ресурс исчезает."""
        response = api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": test_file_in_folder},
        )
        assert response.status_code == 204, response.text
        assert not resource_exists(api_client, test_file_in_folder)

    def test_delete_empty_folder_returns_204_and_removes_resource(
        self, api_client, test_empty_folder
    ):
        """Удаление пустой папки → 204 No Content, папка исчезает."""
        response = api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": test_empty_folder},
        )
        assert response.status_code == 204, response.text
        assert not resource_exists(api_client, test_empty_folder)

    def test_delete_non_empty_folder_returns_202_with_operation_link(
        self, api_client, test_folder_with_files
    ):
        """Удаление непустой папки → 202 Accepted, Link на операцию."""
        response = api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": test_folder_with_files},
        )
        assert response.status_code == 202, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert "/v1/disk/operations/" in data["href"]

        wait_for_operation(api_client, data["href"])
        assert not resource_exists(api_client, test_folder_with_files)

    def test_delete_file_permanently_returns_204(
        self, api_client, test_file_in_folder
    ):
        """Безвозвратное удаление файла → 204, ресурс исчезает."""
        response = api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": test_file_in_folder, "permanently": "true"},
        )
        assert response.status_code == 204, response.text
        assert not resource_exists(api_client, test_file_in_folder)

    def test_delete_file_with_force_async_returns_202(
        self, api_client, test_file_in_folder
    ):
        """force_async=true переводит удаление файла в async → 202."""
        response = api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": test_file_in_folder, "force_async": "true"},
        )
        assert response.status_code == 202, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert "/v1/disk/operations/" in data["href"]

        wait_for_operation(api_client, data["href"])
        assert not resource_exists(api_client, test_file_in_folder)

    def test_delete_with_correct_md5_returns_204(
        self, api_client, test_file_in_folder
    ):
        """Указание корректного md5 → удаление проходит успешно (204)."""
        meta = api_client.get(
            f"{BASE_URL}/resources", params={"path": test_file_in_folder}
        ).json()
        md5 = meta["md5"]

        response = api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": test_file_in_folder, "md5": md5},
        )
        assert response.status_code == 204, response.text
        assert not resource_exists(api_client, test_file_in_folder)

    def test_delete_with_wrong_md5_returns_409_and_keeps_resource(
        self, api_client, test_file_in_folder
    ):
        """Несовпадение md5 → 409 Conflict, файл остаётся на месте."""
        response = api_client.delete(
            f"{BASE_URL}/resources",
            params={
                "path": test_file_in_folder,
                "md5": "00000000000000000000000000000000",
            },
        )
        assert response.status_code == 409, response.text
        assert "error" in response.json()
        assert resource_exists(api_client, test_file_in_folder)

    def test_delete_folder_with_md5_returns_400(
        self, api_client, test_empty_folder
    ):
        """md5 применим только к файлам: для папки → 400."""
        response = api_client.delete(
            f"{BASE_URL}/resources",
            params={
                "path": test_empty_folder,
                "md5": "00000000000000000000000000000000",
            },
        )
        assert response.status_code == 400, response.text
        assert "error" in response.json()

    def test_delete_nonexistent_resource_returns_404(self, api_client):
        """Несуществующий ресурс → 404."""
        response = api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": "app:/no_such_file_xyz.txt"},
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()

    def test_delete_without_path_returns_400(self, api_client):
        """Отсутствует обязательный path → 400."""
        response = api_client.delete(f"{BASE_URL}/resources")
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])