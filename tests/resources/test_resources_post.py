"""
POST-эндпоинты раздела /v1/disk/resources.

Покрываемые эндпоинты:
  1. POST /v1/disk/resources/copy    — копирование файла или папки
  2. POST /v1/disk/resources/move    — перемещение файла или папки
  3. POST /v1/disk/resources/upload  — сохранение файла из интернета на Диск
"""
import pytest
import requests

from config import BASE_URL
from helpers import wait_for_operation, resource_exists


class TestCopyResource:
    """Тесты POST /v1/disk/resources/copy — создание копии файла или папки."""

    def test_copy_file_returns_201_with_link_to_new_resource(
        self, api_client, test_file_in_folder, test_folder
    ):
        """Копирование файла → 201 Created, Link ведёт на метаинформацию копии."""
        dst = f"{test_folder}/copy_of_test_file.txt"
        response = api_client.post(
            f"{BASE_URL}/resources/copy",
            params={"from": test_file_in_folder, "path": dst},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert data["href"].startswith("http")

        meta = api_client.get(
            f"{BASE_URL}/resources", params={"path": dst}
        ).json()
        assert meta["type"] == "file"
        assert meta["size"] == len("Hello, Yandex Disk!")

    def test_copy_non_empty_folder_returns_202_with_operation_link(
        self, api_client, test_non_empty_folder, test_folder
    ):
        """Копирование непустой папки → 202 Accepted, Link на операцию."""
        dst = f"{test_folder}/copy_of_non_empty_folder"
        response = api_client.post(
            f"{BASE_URL}/resources/copy",
            params={"from": test_non_empty_folder, "path": dst},
        )
        assert response.status_code == 202, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert "operations" in data["href"]

        wait_for_operation(api_client, data["href"])
        assert resource_exists(api_client, dst), \
            f"Копия {dst} не появилась после завершения операции"

    def test_copy_with_fields_param_returns_only_requested_keys(
        self, api_client, test_file_in_folder, test_folder
    ):
        """fields ограничивает набор ключей в объекте Link."""
        dst = f"{test_folder}/copy_with_fields.txt"
        response = api_client.post(
            f"{BASE_URL}/resources/copy",
            params={
                "from": test_file_in_folder,
                "path": dst,
                "fields": "href,method",
            },
        )
        assert response.status_code == 201
        assert set(response.json().keys()) == {"href", "method"}

    def test_copy_with_overwrite_true_replaces_existing(
        self, api_client, test_file_in_folder, test_folder
    ):
        """overwrite=true заменяет существующий файл-приёмник."""
        dst = f"{test_folder}/copy_overwrite.txt"
        api_client.post(
            f"{BASE_URL}/resources/copy",
            params={"from": test_file_in_folder, "path": dst},
        )
        response = api_client.post(
            f"{BASE_URL}/resources/copy",
            params={
                "from": test_file_in_folder,
                "path": dst,
                "overwrite": "true",
            },
        )
        assert response.status_code in (201, 202), response.text

        meta = api_client.get(
            f"{BASE_URL}/resources", params={"path": dst}
        ).json()
        assert meta["size"] == len("Hello, Yandex Disk!")

    def test_copy_with_overwrite_false_to_existing_returns_409(
        self, api_client, test_file_in_folder, test_folder
    ):
        """overwrite=false и файл уже есть → 409 Conflict."""
        dst = f"{test_folder}/copy_conflict.txt"
        api_client.post(
            f"{BASE_URL}/resources/copy",
            params={"from": test_file_in_folder, "path": dst},
        )
        response = api_client.post(
            f"{BASE_URL}/resources/copy",
            params={
                "from": test_file_in_folder,
                "path": dst,
                "overwrite": "false",
            },
        )
        assert response.status_code == 409, response.text
        assert "error" in response.json()

    def test_copied_file_downloads_with_same_content(
        self, api_client, test_file_in_folder, test_folder
    ):
        """E2E: содержимое копии совпадает с оригиналом."""
        dst = f"{test_folder}/e2e_copy.txt"
        api_client.post(
            f"{BASE_URL}/resources/copy",
            params={"from": test_file_in_folder, "path": dst},
        )

        link = api_client.get(
            f"{BASE_URL}/resources/download", params={"path": dst}
        ).json()["href"]
        downloaded = requests.get(
            link, headers={"User-Agent": "Mozilla/5.0"}
        )
        assert downloaded.status_code == 200
        assert downloaded.text == "Hello, Yandex Disk!"

    def test_copy_nonexistent_source_returns_404(self, api_client, test_folder):
        """Несуществующий источник → 404."""
        response = api_client.post(
            f"{BASE_URL}/resources/copy",
            params={
                "from": "app:/no_such_file_xyz.txt",
                "path": f"{test_folder}/never_created.txt",
            },
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()

    def test_copy_to_nonexistent_parent_folder_returns_error(
        self, api_client, test_file_in_folder
    ):
        """Родительская папка назначения не существует → 4xx."""
        response = api_client.post(
            f"{BASE_URL}/resources/copy",
            params={
                "from": test_file_in_folder,
                "path": "app:/no_such_folder_xyz/copy.txt",
            },
        )
        assert response.status_code in (404, 409), response.text
        assert "error" in response.json()

    def test_copy_without_from_returns_400(self, api_client, test_folder):
        """Отсутствует обязательный from → 400."""
        response = api_client.post(
            f"{BASE_URL}/resources/copy",
            params={"path": f"{test_folder}/dst.txt"},
        )
        assert response.status_code == 400

    def test_copy_without_path_returns_400(
        self, api_client, test_file_in_folder
    ):
        """Отсутствует обязательный path → 400."""
        response = api_client.post(
            f"{BASE_URL}/resources/copy",
            params={"from": test_file_in_folder},
        )
        assert response.status_code == 400


class TestMoveResource:
    """Тесты POST /v1/disk/resources/move — перемещение файла или папки."""

    def test_move_file_returns_201_and_removes_source(
        self, api_client, test_file_in_folder, test_folder
    ):
        """Перемещение файла → 201, исходный путь исчезает, новый появляется."""
        dst = f"{test_folder}/moved_test_file.txt"
        response = api_client.post(
            f"{BASE_URL}/resources/move",
            params={"from": test_file_in_folder, "path": dst},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert data["href"].startswith("http")

        assert resource_exists(api_client, dst)
        assert not resource_exists(api_client, test_file_in_folder), \
            "Исходный путь не должен существовать после перемещения"

    def test_move_non_empty_folder_returns_202_with_operation_link(
        self, api_client, test_non_empty_folder, test_folder
    ):
        """Перемещение непустой папки → 202 Accepted, Link на операцию."""
        dst = f"{test_folder}/moved_non_empty_folder"
        response = api_client.post(
            f"{BASE_URL}/resources/move",
            params={"from": test_non_empty_folder, "path": dst},
        )
        assert response.status_code == 202, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert "operations" in data["href"]

        wait_for_operation(api_client, data["href"])
        assert resource_exists(api_client, dst)
        assert not resource_exists(api_client, test_non_empty_folder), \
            "Источник не должен существовать после перемещения"

    def test_move_with_fields_param_returns_only_requested_keys(
        self, api_client, test_file_in_folder, test_folder
    ):
        """fields ограничивает набор ключей в объекте Link."""
        dst = f"{test_folder}/move_with_fields.txt"
        response = api_client.post(
            f"{BASE_URL}/resources/move",
            params={
                "from": test_file_in_folder,
                "path": dst,
                "fields": "href,method",
            },
        )
        assert response.status_code == 201
        assert set(response.json().keys()) == {"href", "method"}

    def test_move_with_overwrite_true_replaces_existing(
        self, api_client, test_file_in_folder, test_folder
    ):
        """overwrite=true заменяет существующий файл-приёмник."""
        victim = f"{test_folder}/victim.txt"
        href = api_client.get(
            f"{BASE_URL}/resources/upload",
            params={"path": victim, "overwrite": "true"},
        ).json()["href"]
        requests.put(
            href, data="victim content",
            headers={"Content-Type": "text/plain"},
        )

        response = api_client.post(
            f"{BASE_URL}/resources/move",
            params={
                "from": test_file_in_folder,
                "path": victim,
                "overwrite": "true",
            },
        )
        assert response.status_code in (201, 202), response.text

        meta = api_client.get(
            f"{BASE_URL}/resources", params={"path": victim}
        ).json()
        assert meta["size"] == len("Hello, Yandex Disk!"), \
            "Приёмник должен содержать данные источника после overwrite"

    def test_move_with_overwrite_false_to_existing_returns_409(
        self, api_client, test_file_in_folder, test_folder
    ):
        """overwrite=false и ресурс существует по новому пути → 409."""
        victim = f"{test_folder}/victim_no_overwrite.txt"
        href = api_client.get(
            f"{BASE_URL}/resources/upload",
            params={"path": victim, "overwrite": "true"},
        ).json()["href"]
        requests.put(
            href, data="victim content",
            headers={"Content-Type": "text/plain"},
        )

        response = api_client.post(
            f"{BASE_URL}/resources/move",
            params={
                "from": test_file_in_folder,
                "path": victim,
                "overwrite": "false",
            },
        )
        assert response.status_code == 409, response.text
        assert "error" in response.json()

    def test_moved_file_downloads_with_same_content(
        self, api_client, test_file_in_folder, test_folder
    ):
        """E2E: содержимое файла после перемещения не изменилось."""
        dst = f"{test_folder}/e2e_move.txt"
        api_client.post(
            f"{BASE_URL}/resources/move",
            params={"from": test_file_in_folder, "path": dst},
        )

        link = api_client.get(
            f"{BASE_URL}/resources/download", params={"path": dst}
        ).json()["href"]
        downloaded = requests.get(
            link, headers={"User-Agent": "Mozilla/5.0"}
        )
        assert downloaded.status_code == 200
        assert downloaded.text == "Hello, Yandex Disk!"

    def test_move_nonexistent_source_returns_404(self, api_client, test_folder):
        """Несуществующий источник → 404."""
        response = api_client.post(
            f"{BASE_URL}/resources/move",
            params={
                "from": "app:/no_such_file_xyz.txt",
                "path": f"{test_folder}/never_moved.txt",
            },
        )
        assert response.status_code == 404, response.text
        assert "error" in response.json()

    def test_move_to_nonexistent_parent_folder_returns_error(
        self, api_client, test_file_in_folder
    ):
        """Родительская папка назначения не существует → 4xx."""
        response = api_client.post(
            f"{BASE_URL}/resources/move",
            params={
                "from": test_file_in_folder,
                "path": "app:/no_such_folder_xyz/moved.txt",
            },
        )
        assert response.status_code in (404, 409), response.text
        assert "error" in response.json()

    def test_move_without_from_returns_400(self, api_client, test_folder):
        """Отсутствует from → 400."""
        response = api_client.post(
            f"{BASE_URL}/resources/move",
            params={"path": f"{test_folder}/dst.txt"},
        )
        assert response.status_code == 400

    def test_move_without_path_returns_400(
        self, api_client, test_file_in_folder
    ):
        """Отсутствует path → 400."""
        response = api_client.post(
            f"{BASE_URL}/resources/move",
            params={"from": test_file_in_folder},
        )
        assert response.status_code == 400


class TestUploadFromUrl:
    """Тесты POST /v1/disk/resources/upload — сохранение файла из интернета."""

    def test_upload_from_url_returns_202_with_operation_link(
        self, api_client, test_folder, external_file_url
    ):
        """Загрузка по URL асинхронна: 202 Accepted + Link на операцию."""
        dst = f"{test_folder}/from_url.txt"
        response = api_client.post(
            f"{BASE_URL}/resources/upload",
            params={"url": external_file_url, "path": dst},
        )
        assert response.status_code == 202, response.text
        data = response.json()
        assert data["method"] == "GET"

        href = data["href"]
        assert "/v1/disk/operations/" in href, \
            f"Неожиданный формат href: {href}"
        operation_id = href.rstrip("/").rsplit("/", 1)[-1]
        assert operation_id, "Не удалось извлечь operation_id из href"

    def test_upload_from_url_creates_file_after_operation_completes(
        self, api_client, test_folder, external_file_url
    ):
        """E2E: после завершения операции файл появляется с ненулевым размером."""
        dst = f"{test_folder}/from_url_e2e.txt"
        response = api_client.post(
            f"{BASE_URL}/resources/upload",
            params={"url": external_file_url, "path": dst},
        )
        assert response.status_code == 202
        operation_href = response.json()["href"]

        wait_for_operation(api_client, operation_href, timeout=90)

        assert resource_exists(api_client, dst), \
            f"Файл {dst} не появился после завершения операции"
        meta = api_client.get(
            f"{BASE_URL}/resources", params={"path": dst}
        ).json()
        assert meta["size"] > 0

    def test_upload_with_fields_param_returns_only_requested_keys(
        self, api_client, test_folder, external_file_url
    ):
        """fields ограничивает набор ключей в объекте Link."""
        dst = f"{test_folder}/from_url_fields.txt"
        response = api_client.post(
            f"{BASE_URL}/resources/upload",
            params={
                "url": external_file_url,
                "path": dst,
                "fields": "href,method",
            },
        )
        assert response.status_code == 202
        assert set(response.json().keys()) == {"href", "method"}

    def test_upload_without_url_returns_400(self, api_client, test_folder):
        """Отсутствует обязательный url → 400."""
        response = api_client.post(
            f"{BASE_URL}/resources/upload",
            params={"path": f"{test_folder}/no_url.txt"},
        )
        assert response.status_code == 400

    def test_upload_without_path_returns_400(
        self, api_client, external_file_url
    ):
        """Отсутствует обязательный path → 400."""
        response = api_client.post(
            f"{BASE_URL}/resources/upload",
            params={"url": external_file_url},
        )
        assert response.status_code == 400

    def test_upload_to_nonexistent_folder_returns_error(
        self, api_client, external_file_url
    ):
        """Родительская папка не существует → 4xx."""
        response = api_client.post(
            f"{BASE_URL}/resources/upload",
            params={
                "url": external_file_url,
                "path": "app:/no_such_folder_xyz/file.txt",
            },
        )
        assert response.status_code in (404, 409), response.text
        assert "error" in response.json()

    def test_upload_with_invalid_url_returns_400_or_202_with_failed_operation(
        self, api_client, test_folder
    ):
        """Невалидный URL: либо 400 сразу, либо 202 + failed-операция."""
        dst = f"{test_folder}/invalid_url.txt"
        response = api_client.post(
            f"{BASE_URL}/resources/upload",
            params={"url": "not-a-valid-url", "path": dst},
        )
        if response.status_code == 400:
            assert "error" in response.json()
        else:
            assert response.status_code == 202
            with pytest.raises(AssertionError, match="завершилась с ошибкой"):
                wait_for_operation(
                    api_client, response.json()["href"], timeout=30
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])