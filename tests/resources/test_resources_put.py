import pytest

from config import BASE_URL
from helpers import resource_exists


class TestCreateFolder:
    """Тесты PUT /v1/disk/resources — создание папки."""

    def test_create_folder_returns_201_with_link_to_metadata(
        self, api_client, test_folder
    ):
        """Создание папки → 201 Created, Link ведёт на метаинформацию."""
        new_folder = f"{test_folder}/created_folder"
        response = api_client.put(
            f"{BASE_URL}/resources", params={"path": new_folder}
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert data["href"].startswith("http")

        meta = api_client.get(
            f"{BASE_URL}/resources", params={"path": new_folder}
        ).json()
        assert meta["type"] == "dir"
        assert meta["name"] == "created_folder"

    def test_create_folder_with_fields_param_returns_only_requested_keys(
        self, api_client, test_folder
    ):
        """fields ограничивает набор ключей в объекте Link."""
        new_folder = f"{test_folder}/folder_with_fields"
        response = api_client.put(
            f"{BASE_URL}/resources",
            params={"path": new_folder, "fields": "href,method"},
        )
        assert response.status_code == 201
        assert set(response.json().keys()) == {"href", "method"}

    def test_create_existing_folder_returns_409(
        self, api_client, test_folder
    ):
        """Папка уже существует → 409 Conflict."""
        existing = f"{test_folder}/existing_folder"
        api_client.put(f"{BASE_URL}/resources", params={"path": existing})

        response = api_client.put(
            f"{BASE_URL}/resources", params={"path": existing}
        )
        assert response.status_code == 409, response.text
        assert "error" in response.json()

    def test_create_folder_without_path_returns_400(self, api_client):
        """Отсутствует обязательный path → 400."""
        response = api_client.put(f"{BASE_URL}/resources")
        assert response.status_code == 400

    def test_create_folder_in_nonexistent_parent_returns_error(
        self, api_client
    ):
        """Родительская папка не существует → 4xx."""
        response = api_client.put(
            f"{BASE_URL}/resources",
            params={"path": "app:/no_such_parent_xyz/child"},
        )
        assert response.status_code in (404, 409), response.text
        assert "error" in response.json()

    def test_create_folder_with_cyrillic_name_returns_201(
        self, api_client, test_folder
    ):
        """Папка с кириллическим именем создаётся корректно
        (проверка URL-encoding)."""
        new_folder = f"{test_folder}/папка_с_кириллицей"
        response = api_client.put(
            f"{BASE_URL}/resources", params={"path": new_folder}
        )
        assert response.status_code == 201, response.text
        assert resource_exists(api_client, new_folder)


class TestPublishResource:
    """Тесты PUT /v1/disk/resources/publish — публикация ресурса."""

    def test_publish_file_returns_link_to_metadata(
        self, api_client, unpublished_file
    ):
        """Публикация файла → 200 OK с объектом Link."""
        response = api_client.put(
            f"{BASE_URL}/resources/publish",
            params={"path": unpublished_file},
        )
        assert response.status_code == 200, response.text
        link = response.json()
        assert link["method"] == "GET"
        assert link["href"].startswith("http")

    def test_publish_link_leads_to_metadata_with_public_url(
        self, api_client, unpublished_file
    ):
        """Идём по href из ответа publish — в метаданных должны быть
        public_url и public_key, то есть публикация реально сработала."""
        publish_resp = api_client.put(
            f"{BASE_URL}/resources/publish",
            params={"path": unpublished_file},
        )
        link_href = publish_resp.json()["href"]

        meta_resp = api_client.get(link_href)
        assert meta_resp.status_code == 200, meta_resp.text
        meta = meta_resp.json()
        assert meta["public_url"].startswith("https://")
        assert meta["public_key"]

    def test_publish_twice_keeps_same_public_url(
        self, api_client, unpublished_file
    ):
        """Повторная публикация не создаёт новую ссылку — public_url не меняется."""
        first_link = api_client.put(
            f"{BASE_URL}/resources/publish",
            params={"path": unpublished_file},
        ).json()["href"]
        first_url = api_client.get(first_link).json()["public_url"]

        second_link = api_client.put(
            f"{BASE_URL}/resources/publish",
            params={"path": unpublished_file},
        ).json()["href"]
        second_url = api_client.get(second_link).json()["public_url"]

        assert first_url == second_url

    def test_publish_with_fields_param_returns_only_requested_link_keys(
        self, api_client, unpublished_file
    ):
        """fields ограничивает набор ключей в объекте Link."""
        response = api_client.put(
            f"{BASE_URL}/resources/publish",
            params={"path": unpublished_file, "fields": "href,method"},
        )
        assert response.status_code == 200
        assert set(response.json().keys()) == {"href", "method"}

    def test_publish_nonexistent_resource_returns_404(self, api_client):
        """Несуществующий ресурс → 404."""
        response = api_client.put(
            f"{BASE_URL}/resources/publish",
            params={"path": "app:/no_such_file_xyz.txt"},
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()

    def test_publish_without_path_returns_400(self, api_client):
        """Отсутствует обязательный path → 400."""
        response = api_client.put(f"{BASE_URL}/resources/publish")
        assert response.status_code == 400


class TestUnpublishResource:
    """Тесты PUT /v1/disk/resources/unpublish — отмена публикации."""

    def test_unpublish_published_file_returns_200(
        self, api_client, unpublished_file
    ):
        """Отмена публикации ранее опубликованного файла → 200 OK."""
        api_client.put(
            f"{BASE_URL}/resources/publish",
            params={"path": unpublished_file},
        )
        response = api_client.put(
            f"{BASE_URL}/resources/unpublish",
            params={"path": unpublished_file},
        )
        assert response.status_code == 200, response.text

    def test_unpublished_file_no_longer_has_public_url(
        self, api_client, unpublished_file
    ):
        """После отмены публикации public_url отсутствует в метаинформации."""
        api_client.put(
            f"{BASE_URL}/resources/publish",
            params={"path": unpublished_file},
        )
        api_client.put(
            f"{BASE_URL}/resources/unpublish",
            params={"path": unpublished_file},
        )

        meta = api_client.get(
            f"{BASE_URL}/resources", params={"path": unpublished_file}
        ).json()
        assert "public_url" not in meta
        assert "public_key" not in meta

    def test_unpublish_non_published_resource_returns_200(
        self, api_client, unpublished_file
    ):
        """Отмена публикации неопубликованного ресурса → 200 OK
        (идемпотентное поведение API)."""
        response = api_client.put(
            f"{BASE_URL}/resources/unpublish",
            params={"path": unpublished_file},
        )
        assert response.status_code == 200, response.text

    def test_unpublish_with_fields_param_returns_only_requested_link_keys(
        self, api_client, unpublished_file
    ):
        """fields ограничивает набор ключей в объекте Link."""
        api_client.put(
            f"{BASE_URL}/resources/publish",
            params={"path": unpublished_file},
        )
        response = api_client.put(
            f"{BASE_URL}/resources/unpublish",
            params={"path": unpublished_file, "fields": "href,method"},
        )
        assert response.status_code == 200
        assert set(response.json().keys()) == {"href", "method"}

    def test_unpublish_nonexistent_resource_returns_404(self, api_client):
        """Несуществующий ресурс → 404."""
        response = api_client.put(
            f"{BASE_URL}/resources/unpublish",
            params={"path": "app:/no_such_file_xyz.txt"},
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()

    def test_unpublish_without_path_returns_400(self, api_client):
        """Отсутствует обязательный path → 400."""
        response = api_client.put(f"{BASE_URL}/resources/unpublish")
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])