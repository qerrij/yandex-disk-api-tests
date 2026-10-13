import pytest

from config import BASE_URL


TRASH_RESOURCES = f"{BASE_URL}/trash/resources"


class TestGetTrashResourceMetadata:
    """Тесты GET /v1/disk/trash/resources — метаинформация о ресурсе в Корзине."""

    def test_trashed_file_returns_metadata(
        self, api_client, trashed_file
    ):
        """Метаинформация о файле в Корзине: type=file, есть size и md5."""
        response = api_client.get(
            TRASH_RESOURCES, params={"path": trashed_file}
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["type"] == "file"
        assert data["size"] == len("trash file content")
        assert "md5" in data
        assert data["mime_type"].startswith("text/")

    def test_trashed_file_has_origin_path(
        self, api_client, trashed_file
    ):
        """Для файла из Корзины возвращается origin_path — путь до удаления."""
        response = api_client.get(
            TRASH_RESOURCES, params={"path": trashed_file}
        )
        assert response.status_code == 200
        data = response.json()
        assert "origin_path" in data
        assert data["origin_path"].startswith("disk:/")

    def test_trashed_folder_returns_metadata(
        self, api_client, trashed_folder
    ):
        """Метаинформация о папке в Корзине: type=dir, есть _embedded."""
        response = api_client.get(
            TRASH_RESOURCES, params={"path": trashed_folder}
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["type"] == "dir"
        assert "_embedded" in data

    def test_trash_root_returns_resource_list(
        self, api_client, trashed_file
    ):
        """Запрос корня Корзины (path=/) возвращает ResourceList."""
        response = api_client.get(
            TRASH_RESOURCES, params={"path": "/"}
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["type"] == "dir"
        assert "_embedded" in data
        embedded = data["_embedded"]
        assert "items" in embedded
        assert "limit" in embedded
        assert "offset" in embedded

    def test_fields_param_returns_only_requested_attributes(
        self, api_client, trashed_file
    ):
        """fields фильтрует набор атрибутов в ответе."""
        response = api_client.get(
            TRASH_RESOURCES,
            params={"path": trashed_file, "fields": "name,type,size"},
        )
        assert response.status_code == 200, response.text
        assert set(response.json().keys()) == {"name", "type", "size"}

    def test_limit_param_caps_items_count(
        self, api_client, trashed_files
    ):
        """limit ограничивает количество элементов в списке Корзины."""
        response = api_client.get(
            TRASH_RESOURCES, params={"path": "/", "limit": 1}
        )
        assert response.status_code == 200
        embedded = response.json()["_embedded"]
        assert embedded["limit"] == 1
        assert len(embedded["items"]) <= 1
        assert embedded["total"] >= 3

    def test_offset_param_skips_items(
        self, api_client, trashed_files
    ):
        """offset задаёт смещение в списке Корзины."""
        response = api_client.get(
            TRASH_RESOURCES, params={"path": "/", "offset": 1}
        )
        assert response.status_code == 200
        assert response.json()["_embedded"]["offset"] == 1

    def test_nonexistent_path_returns_404(self, api_client):
        """Несуществующий путь в Корзине → 404."""
        response = api_client.get(
            TRASH_RESOURCES,
            params={"path": "trash:/no_such_file_xyz_12345"},
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])