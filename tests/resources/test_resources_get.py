import time

import pytest
import requests

from config import BASE_URL


class TestGetResourceMetadata:

    def test_folder_returns_directory_metadata(self, api_client, test_folder):
        response = api_client.get(
            f"{BASE_URL}/resources", params={"path": test_folder}
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["type"] == "dir"
        assert data["name"].startswith("test_folder_")
        assert data["path"].startswith("disk:/")
        assert "_embedded" in data and "items" in data["_embedded"]

    def test_file_returns_file_metadata_with_size_and_hash(
        self, api_client, test_file_in_folder
    ):
        response = api_client.get(
            f"{BASE_URL}/resources", params={"path": test_file_in_folder}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "file"
        assert data["name"] == "test_file.txt"
        assert data["size"] == len("Hello, Yandex Disk!")
        assert "md5" in data
        assert data["mime_type"].startswith("text/")

    def test_root_path_returns_disk_root_metadata(self, api_client):
        response = api_client.get(
            f"{BASE_URL}/resources", params={"path": "app:/"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "dir"
        assert data["name"]
        assert "_embedded" in data

    def test_fields_param_returns_only_requested_attributes(
        self, api_client, test_folder
    ):
        response = api_client.get(
            f"{BASE_URL}/resources",
            params={"path": test_folder, "fields": "name,type"},
        )
        assert response.status_code == 200
        assert set(response.json().keys()) == {"name", "type"}

    def test_limit_param_caps_items_count(self, api_client, test_folder_with_files):
        response = api_client.get(
            f"{BASE_URL}/resources",
            params={"path": test_folder_with_files, "limit": 1},
        )
        assert response.status_code == 200
        embedded = response.json()["_embedded"]
        assert embedded["limit"] == 1
        assert len(embedded["items"]) <= 1
        assert embedded["total"] >= 3

    def test_sort_by_name_returns_items_ascending(
        self, api_client, test_folder_with_files
    ):
        response = api_client.get(
            f"{BASE_URL}/resources",
            params={"path": test_folder_with_files, "sort": "name"},
        )
        assert response.status_code == 200
        names = [i["name"] for i in response.json()["_embedded"]["items"]]
        assert names == sorted(names)

    def test_sort_desc_returns_items_in_reverse_order(
        self, api_client, test_folder_with_files
    ):
        """Yandex нормализует поле sort в ответе (без '-'),
        поэтому направление проверяем по фактическому порядку."""
        response = api_client.get(
            f"{BASE_URL}/resources",
            params={"path": test_folder_with_files, "sort": "-name"},
        )
        assert response.status_code == 200
        names = [i["name"] for i in response.json()["_embedded"]["items"]]
        assert names == sorted(names, reverse=True)

    def test_nonexistent_path_returns_404_with_error_payload(self, api_client):
        response = api_client.get(
            f"{BASE_URL}/resources",
            params={"path": "app:/no_such_folder_xyz_12345"},
        )
        assert response.status_code == 404
        body = response.json()
        assert "error" in body and "message" in body

    def test_missing_path_returns_400(self, api_client):
        response = api_client.get(f"{BASE_URL}/resources")
        assert response.status_code == 400


class TestGetDownloadLink:

    def test_file_returns_link_with_get_method(
        self, api_client, test_file_in_folder
    ):
        response = api_client.get(
            f"{BASE_URL}/resources/download",
            params={"path": test_file_in_folder},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["method"] == "GET"
        assert data["href"].startswith("http")

    def test_link_downloads_actual_file_content(
        self, api_client, test_file_in_folder
    ):
        """E2E: получаем ссылку, качаем по ней, сверяем содержимое."""
        link_resp = api_client.get(
            f"{BASE_URL}/resources/download",
            params={"path": test_file_in_folder},
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

    def test_fields_param_returns_only_href_and_method(
        self, api_client, test_file_in_folder
    ):
        response = api_client.get(
            f"{BASE_URL}/resources/download",
            params={"path": test_file_in_folder, "fields": "href,method"},
        )
        assert response.status_code == 200
        assert set(response.json().keys()) == {"href", "method"}

    def test_nonexistent_file_returns_404(self, api_client):
        response = api_client.get(
            f"{BASE_URL}/resources/download",
            params={"path": "app:/no_such_file_98765.txt"},
        )
        assert response.status_code == 404
        assert "error" in response.json()

    def test_missing_path_returns_400(self, api_client):
        response = api_client.get(f"{BASE_URL}/resources/download")
        assert response.status_code == 400


class TestGetFlatFileList:

    def test_default_request_returns_items_and_default_limit(
        self, api_client, test_file_in_folder
    ):
        response = api_client.get(f"{BASE_URL}/resources/files")
        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data["items"], list)
        assert data["limit"] == 20

    def test_limit_param_caps_items_count(self, api_client, test_folder_with_files):
        response = api_client.get(
            f"{BASE_URL}/resources/files", params={"limit": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 2
        assert len(data["items"]) <= 2

    def test_media_type_image_returns_only_images(self, api_client, test_image_file):
        response = api_client.get(
            f"{BASE_URL}/resources/files", params={"media_type": "image"}
        )
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["mime_type"].startswith("image/"), \
                f"Неожиданный mime_type: {item['mime_type']}"

    def test_media_type_comma_list_returns_only_requested_types(
        self, api_client, test_file_in_folder, test_image_file
    ):
        response = api_client.get(
            f"{BASE_URL}/resources/files",
            params={"media_type": "image,text"},
        )
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["mime_type"].startswith(("image/", "text/"))


class TestGetLastUploaded:

    def test_default_request_returns_items_and_limit(
        self, api_client, test_file_in_folder
    ):
        response = api_client.get(f"{BASE_URL}/resources/last-uploaded")
        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data["items"], list)
        assert "limit" in data

    def test_limit_param_caps_items_count(self, api_client, test_file_in_folder):
        response = api_client.get(
            f"{BASE_URL}/resources/last-uploaded", params={"limit": 1}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 1
        assert len(data["items"]) <= 1

    def test_media_type_text_returns_only_text_files(
        self, api_client, test_file_in_folder
    ):
        response = api_client.get(
            f"{BASE_URL}/resources/last-uploaded",
            params={"media_type": "text"},
        )
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert (
                item["mime_type"].startswith("text/")
                or item.get("media_type") == "text"
            )

    def test_recently_uploaded_file_appears_in_list(
        self, api_client, test_file_in_folder
    ):
        """E2E: только что загруженный файл должен быть в списке.
        Реальные пути содержат префикс disk:/Приложения/..., поэтому
        матчим по суффиксу."""
        response = api_client.get(
            f"{BASE_URL}/resources/last-uploaded", params={"limit": 100}
        )
        assert response.status_code == 200
        paths = [i["path"] for i in response.json()["items"]]
        folder_name = test_file_in_folder.split("/")[-2]
        assert any(
            folder_name in p and p.endswith("/test_file.txt") for p in paths
        ), f"Не найден {folder_name}/test_file.txt. Пути: {paths}"


class TestGetPublicResources:

    def test_default_request_returns_published_resources(
        self, api_client, published_file
    ):
        response = api_client.get(f"{BASE_URL}/resources/public")
        assert response.status_code == 200, response.text
        assert isinstance(response.json()["items"], list)

    def test_type_file_returns_only_files(self, api_client, published_file):
        response = api_client.get(
            f"{BASE_URL}/resources/public", params={"type": "file"}
        )
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["type"] == "file"

    def test_type_dir_returns_only_folders(self, api_client, published_file):
        response = api_client.get(
            f"{BASE_URL}/resources/public", params={"type": "dir"}
        )
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["type"] == "dir"


class TestGetUploadLink:

    def test_new_file_returns_put_link_with_operation_id(
        self, api_client, test_folder
    ):
        response = api_client.get(
            f"{BASE_URL}/resources/upload",
            params={"path": f"{test_folder}/brand_new.txt", "overwrite": "true"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["method"] == "PUT"
        assert data["href"].startswith("http")
        assert data.get("operation_id")

    def test_upload_via_link_saves_file_with_correct_size(
        self, api_client, test_folder
    ):
        """E2E: получаем ссылку → PUT содержимого → файл появился с нужным размером."""
        file_path = f"{test_folder}/uploaded_via_link.txt"
        content = "Uploaded through upload link"

        href = api_client.get(
            f"{BASE_URL}/resources/upload",
            params={"path": file_path, "overwrite": "true"},
        ).json()["href"]

        put_resp = requests.put(
            href, data=content, headers={"Content-Type": "text/plain"}
        )
        assert put_resp.status_code == 201, put_resp.text

        meta = api_client.get(
            f"{BASE_URL}/resources", params={"path": file_path}
        ).json()
        assert meta["type"] == "file"
        assert meta["size"] == len(content)

    def test_existing_file_without_overwrite_returns_409(
        self, api_client, test_file_in_folder
    ):
        response = api_client.get(
            f"{BASE_URL}/resources/upload",
            params={"path": test_file_in_folder, "overwrite": "false"},
        )
        assert response.status_code == 409
        assert "error" in response.json()

    def test_existing_file_with_overwrite_returns_new_link(
        self, api_client, test_file_in_folder
    ):
        response = api_client.get(
            f"{BASE_URL}/resources/upload",
            params={"path": test_file_in_folder, "overwrite": "true"},
        )
        assert response.status_code == 200
        assert response.json()["href"].startswith("http")

    def test_nonexistent_parent_folder_returns_error(self, api_client):
        """API возвращает 409 с DiskPathDoesntExistsError."""
        response = api_client.get(
            f"{BASE_URL}/resources/upload",
            params={
                "path": "app:/no_such_folder_xyz/file.txt",
                "overwrite": "true",
            },
        )
        assert response.status_code in (404, 409), response.text
        assert "error" in response.json()

    def test_fields_param_returns_only_href_and_method(
        self, api_client, test_folder
    ):
        response = api_client.get(
            f"{BASE_URL}/resources/upload",
            params={
                "path": f"{test_folder}/with_fields.txt",
                "overwrite": "true",
                "fields": "href,method",
            },
        )
        assert response.status_code == 200
        assert set(response.json().keys()) == {"href", "method"}

    def test_missing_path_returns_400(self, api_client):
        response = api_client.get(f"{BASE_URL}/resources/upload")
        assert response.status_code == 400

    def test_upload_link_for_folder_path_returns_error(
        self, api_client, test_folder
    ):
        response = api_client.get(
            f"{BASE_URL}/resources/upload",
            params={"path": test_folder, "overwrite": "true"},
        )
        assert response.status_code in (400, 409), response.text
        assert "error" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])