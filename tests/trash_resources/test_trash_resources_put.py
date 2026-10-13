"""
PUT-эндпоинт раздела /v1/disk/trash/resources.

Покрываемый эндпоинт:
  PUT /v1/disk/trash/resources/restore — восстановление ресурса из Корзины
"""
import uuid

import pytest

from config import BASE_URL
from helpers import wait_for_operation, resource_exists


RESTORE = f"{BASE_URL}/trash/resources/restore"


class TestRestoreFromTrash:
    """Тесты PUT /v1/disk/trash/resources/restore."""

    def test_restore_file_returns_201_with_link(
        self, api_client, restorable_file
    ):
        """Восстановление файла → 201 Created с Link на восстановленный ресурс."""
        response = api_client.put(
            RESTORE, params={"path": restorable_file["trash_path"]}
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert data["href"].startswith("http")

    def test_restored_file_appears_at_original_path(
        self, api_client, restorable_file
    ):
        """E2E: после восстановления файл существует по исходному пути."""
        response = api_client.put(
            RESTORE, params={"path": restorable_file["trash_path"]}
        )
        assert response.status_code == 201
        assert resource_exists(api_client, restorable_file["original"])

    def test_restore_with_name_param_renames_resource(
        self, api_client, restorable_file
    ):
        """Параметр name восстанавливает ресурс под другим именем
        в той же папке."""
        new_name = f"renamed_{uuid.uuid4().hex[:8]}.txt"
        new_path = f"app:/{new_name}"
        restorable_file["cleanup_paths"].append(new_path)

        response = api_client.put(
            RESTORE,
            params={
                "path": restorable_file["trash_path"],
                "name": new_name,
            },
        )
        assert response.status_code == 201, response.text
        assert resource_exists(api_client, new_path)

        # Оригинального файла быть не должно
        assert not resource_exists(api_client, restorable_file["original"])

    def test_restore_folder_returns_link_to_restored_folder(
        self, api_client, restorable_folder
    ):
        """Восстановление папки → 201 Created."""
        response = api_client.put(
            RESTORE, params={"path": restorable_folder["trash_path"]}
        )
        assert response.status_code == 201, response.text
        assert resource_exists(api_client, restorable_folder["original"])

    def test_restore_with_force_async_returns_operation_link(
        self, api_client, restorable_file
    ):
        """force_async=true переводит восстановление в async → 202."""
        response = api_client.put(
            RESTORE,
            params={
                "path": restorable_file["trash_path"],
                "force_async": "true",
            },
        )
        assert response.status_code == 202, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert "/v1/disk/operations/" in data["href"]

        wait_for_operation(api_client, data["href"])
        assert resource_exists(api_client, restorable_file["original"])

    def test_restore_with_fields_param_returns_filtered_link(
        self, api_client, restorable_file
    ):
        """fields ограничивает набор ключей в объекте Link."""
        response = api_client.put(
            RESTORE,
            params={
                "path": restorable_file["trash_path"],
                "fields": "href,method",
            },
        )
        assert response.status_code == 201
        assert set(response.json().keys()) == {"href", "method"}

    def test_restore_with_overwrite_true_replaces_existing(
        self, api_client, restorable_file
    ):
        """overwrite=true позволяет восстановить файл поверх существующего."""
        conflict_path = restorable_file["original"]
        api_client.put(f"{BASE_URL}/resources", params={"path": conflict_path})

        response = api_client.put(
            RESTORE,
            params={
                "path": restorable_file["trash_path"],
                "overwrite": "true",
            },
        )
        assert response.status_code in (201, 202), response.text
        assert resource_exists(api_client, conflict_path)

    def test_restore_nonexistent_path_returns_404(self, api_client):
        """Несуществующий путь в Корзине → 404."""
        response = api_client.put(
            RESTORE, params={"path": "trash:/no_such_file_xyz_12345"}
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()

    def test_restore_without_path_returns_400(self, api_client):
        """Отсутствует обязательный path → 400."""
        response = api_client.put(RESTORE)
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])