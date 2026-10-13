import pytest

from config import BASE_URL
from helpers import wait_for_operation


TRASH_RESOURCES = f"{BASE_URL}/trash/resources"


class TestDeleteTrashResource:
    """Тесты DELETE /v1/disk/trash/resources — удаление ресурса из Корзины."""

    def test_delete_file_from_trash_returns_204(
        self, api_client, trashed_file
    ):
        """Удаление файла из Корзины → 204 No Content, файл исчезает."""
        response = api_client.delete(
            TRASH_RESOURCES, params={"path": trashed_file}
        )
        assert response.status_code == 204, response.text

        check = api_client.get(
            TRASH_RESOURCES, params={"path": trashed_file}
        )
        assert check.status_code == 404, \
            "Файл не удалён из Корзины после 204"

    def test_delete_folder_from_trash_returns_204(
        self, api_client, trashed_folder
    ):
        """Удаление папки из Корзины → 204 No Content, папка исчезает."""
        response = api_client.delete(
            TRASH_RESOURCES, params={"path": trashed_folder}
        )
        assert response.status_code == 204, response.text

        check = api_client.get(
            TRASH_RESOURCES, params={"path": trashed_folder}
        )
        assert check.status_code == 404

    def test_delete_with_force_async_returns_202(
        self, api_client, trashed_file
    ):
        """force_async=true переводит удаление в async → 202 с Link на операцию."""
        response = api_client.delete(
            TRASH_RESOURCES,
            params={"path": trashed_file, "force_async": "true"},
        )
        assert response.status_code == 202, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert "/v1/disk/operations/" in data["href"]

        wait_for_operation(api_client, data["href"])

        check = api_client.get(
            TRASH_RESOURCES, params={"path": trashed_file}
        )
        assert check.status_code == 404, \
            "Файл не удалён после завершения async-операции"

    def test_delete_nonexistent_path_returns_404(self, api_client):
        """Несуществующий путь в Корзине → 404."""
        response = api_client.delete(
            TRASH_RESOURCES,
            params={"path": "trash:/no_such_file_xyz_12345"},
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()

    def test_delete_disk_path_returns_error(
        self, api_client, test_file_in_folder
    ):
        """Путь на Диске (не в Корзине) → ошибка."""
        response = api_client.delete(
            TRASH_RESOURCES, params={"path": test_file_in_folder}
        )
        assert 400 <= response.status_code < 500, response.text
        assert "error" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])