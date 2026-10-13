import uuid

import pytest

from config import BASE_URL


SAVE_TO_DISK = f"{BASE_URL}/public/resources/save-to-disk"


@pytest.fixture
def saved_paths(api_client):
    """Собирает пути сохранённых файлов и удаляет их после теста."""
    paths = []
    yield paths
    for p in paths:
        api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": p, "permanently": "true"},
        )


def _save_to_disk(api_client, public_url, name=None, path=None):
    """Сохраняет публичный ресурс и возвращает метаданные сохранённого файла."""
    params = {"public_key": public_url}
    if name:
        params["name"] = name
    if path:
        params["path"] = path

    response = api_client.post(SAVE_TO_DISK, params=params)
    assert response.status_code == 201, response.text

    link = response.json()
    return api_client.get(link["href"]).json()


class TestSavePublicResourceToDisk:
    """Тесты POST /v1/disk/public/resources/save-to-disk."""

    def test_save_public_file_returns_link_to_saved_resource(
        self, api_client, published_file_meta, saved_paths
    ):
        """Сохранение публичного файла → 201 Created с Link на новый ресурс."""
        unique_name = f"saved_{uuid.uuid4().hex[:10]}.txt"

        response = api_client.post(
            SAVE_TO_DISK,
            params={
                "public_key": published_file_meta["public_url"],
                "name": unique_name,
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert data["href"].startswith("http")

        saved_paths.append(api_client.get(data["href"]).json()["path"])

    def test_saved_file_exists_with_correct_content(
        self, api_client, published_file_meta, saved_paths
    ):
        """E2E: сохранённый файл имеет то же содержимое, что и публичный."""
        unique_name = f"e2e_{uuid.uuid4().hex[:10]}.txt"
        meta = _save_to_disk(
            api_client,
            public_url=published_file_meta["public_url"],
            name=unique_name,
        )
        saved_paths.append(meta["path"])

        assert meta["type"] == "file"
        assert meta["size"] == len("Hello, Yandex Disk!")

    def test_save_nested_file_from_public_folder(
        self, api_client, published_folder_meta, saved_paths
    ):
        """Сохранение файла из публичной папки по параметру path."""
        unique_name = f"nested_{uuid.uuid4().hex[:10]}.txt"
        meta = _save_to_disk(
            api_client,
            public_url=published_folder_meta["public_url"],
            path="/a.txt",
            name=unique_name,
        )
        saved_paths.append(meta["path"])

        assert meta["size"] == len("content of a.txt")

    def test_name_param_controls_saved_file_name(
        self, api_client, published_file_meta, saved_paths
    ):
        """Параметр name задаёт имя, под которым файл сохраняется в «Загрузки»."""
        custom_name = f"renamed_{uuid.uuid4().hex[:10]}.txt"
        meta = _save_to_disk(
            api_client,
            public_url=published_file_meta["public_url"],
            name=custom_name,
        )
        saved_paths.append(meta["path"])

        assert meta["name"] == custom_name

    def test_nonexistent_public_key_returns_404(self, api_client):
        """Несуществующий public_key → 404."""
        response = api_client.post(
            SAVE_TO_DISK,
            params={
                "public_key": "no-such-public-key-xyz-12345",
                "name": "should_not_appear.txt",
            },
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()

    def test_missing_public_key_returns_400(self, api_client):
        """Отсутствует обязательный public_key → 400."""
        response = api_client.post(
            SAVE_TO_DISK, params={"name": "x.txt"}
        )
        assert response.status_code == 400

    def test_nonexistent_path_in_public_folder_returns_error(
        self, api_client, published_folder_meta
    ):
        """path указывает на несуществующий файл в публичной папке → 4xx."""
        response = api_client.post(
            SAVE_TO_DISK,
            params={
                "public_key": published_folder_meta["public_url"],
                "path": "/no_such_file.txt",
                "name": "never_saved.txt",
            },
        )
        assert 400 <= response.status_code < 500, response.text
        assert "error" in response.json()