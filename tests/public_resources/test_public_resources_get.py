"""
GET-эндпоинты раздела /v1/disk/public/resources.

Покрываемые эндпоинты:
  1. GET /v1/disk/public/resources           — метаинформация о публичном ресурсе
  2. GET /v1/disk/public/resources/download  — ссылка на скачивание публичного ресурса

Эндпоинты публичного раздела доступны без OAuth-токена: доступ
осуществляется по public_key или публичной ссылке.
"""
import time

import requests

from config import BASE_URL


PUBLIC_RESOURCES = f"{BASE_URL}/public/resources"


class TestGetPublicResourceMetadata:
    """Тесты GET /v1/disk/public/resources — метаинформация о публичном ресурсе."""

    def test_file_returns_metadata_without_oauth(
        self, anonymous_client, published_file_meta
    ):
        """Публичный файл доступен без OAuth, метаданные содержат размер и хэш."""
        response = anonymous_client.get(
            PUBLIC_RESOURCES,
            params={"public_key": published_file_meta["public_key"]},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["type"] == "file"
        assert data["name"] == "test_file.txt"
        assert data["size"] == len("Hello, Yandex Disk!")
        assert "md5" in data

    def test_folder_returns_embedded_items(
        self, anonymous_client, published_folder_meta
    ):
        """Для публичной папки возвращается _embedded.items с вложениями."""
        response = anonymous_client.get(
            PUBLIC_RESOURCES,
            params={"public_key": published_folder_meta["public_key"]},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["type"] == "dir"
        assert "_embedded" in data
        names = {i["name"] for i in data["_embedded"]["items"]}
        assert names == {"a.txt", "b.txt"}

    def test_path_returns_nested_resource_metadata(
        self, anonymous_client, published_folder_meta
    ):
        """path к вложенному файлу возвращает его метаинформацию."""
        response = anonymous_client.get(
            PUBLIC_RESOURCES,
            params={
                "public_key": published_folder_meta["public_key"],
                "path": "/a.txt",
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["type"] == "file"
        assert data["name"] == "a.txt"
        assert data["size"] == len("content of a.txt")

    def test_limit_param_caps_items_count(
        self, anonymous_client, published_folder_meta
    ):
        """limit ограничивает количество вложенных ресурсов."""
        response = anonymous_client.get(
            PUBLIC_RESOURCES,
            params={
                "public_key": published_folder_meta["public_key"],
                "limit": 1,
            },
        )
        assert response.status_code == 200
        embedded = response.json()["_embedded"]
        assert embedded["limit"] == 1
        assert len(embedded["items"]) <= 1
        assert embedded["total"] >= 2

    def test_nonexistent_public_key_returns_404(self, anonymous_client):
        """Несуществующий public_key → 404."""
        response = anonymous_client.get(
            PUBLIC_RESOURCES,
            params={"public_key": "no-such-public-key-xyz-12345"},
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()

    def test_missing_public_key_returns_400(self, anonymous_client):
        """Отсутствует обязательный public_key → 400."""
        response = anonymous_client.get(PUBLIC_RESOURCES)
        assert response.status_code == 400

    def test_nonexistent_path_in_public_folder_returns_404(
        self, anonymous_client, published_folder_meta
    ):
        """Несуществующий path внутри публичной папки → 404."""
        response = anonymous_client.get(
            PUBLIC_RESOURCES,
            params={
                "public_key": published_folder_meta["public_key"],
                "path": "/no_such_file.txt",
            },
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()


class TestGetPublicDownloadLink:
    """Тесты GET /v1/disk/public/resources/download — ссылка на скачивание."""

    def test_file_returns_link_without_oauth(
        self, anonymous_client, published_file_meta
    ):
        """Ссылка на скачивание публичного файла доступна без OAuth."""
        response = anonymous_client.get(
            f"{PUBLIC_RESOURCES}/download",
            params={"public_key": published_file_meta["public_key"]},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert data["href"].startswith("http")

    def test_link_downloads_actual_file_content(
        self, anonymous_client, published_file_meta
    ):
        """E2E: по полученной ссылке реально скачивается содержимое файла."""
        link_resp = anonymous_client.get(
            f"{PUBLIC_RESOURCES}/download",
            params={"public_key": published_file_meta["public_key"]},
        )
        assert link_resp.status_code == 200
        href = link_resp.json()["href"]

        for _ in range(5):
            download_resp = requests.get(
                href, headers={"User-Agent": "Mozilla/5.0"}
            )
            if download_resp.status_code == 200:
                break
            time.sleep(2)

        assert download_resp.status_code == 200, download_resp.text
        assert download_resp.text == "Hello, Yandex Disk!"

    def test_nested_file_via_path_param(
        self, anonymous_client, published_folder_meta
    ):
        """path=/a.txt возвращает ссылку на вложенный файл."""
        response = anonymous_client.get(
            f"{PUBLIC_RESOURCES}/download",
            params={
                "public_key": published_folder_meta["public_key"],
                "path": "/a.txt",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["href"].startswith("http")

    def test_nonexistent_public_key_returns_404(self, anonymous_client):
        """Несуществующий public_key → 404."""
        response = anonymous_client.get(
            f"{PUBLIC_RESOURCES}/download",
            params={"public_key": "no-such-public-key-xyz-12345"},
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()

    def test_missing_public_key_returns_400(self, anonymous_client):
        """Отсутствует обязательный public_key → 400."""
        response = anonymous_client.get(f"{PUBLIC_RESOURCES}/download")
        assert response.status_code == 400