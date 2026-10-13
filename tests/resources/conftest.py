import uuid

import pytest

from config import BASE_URL
from helpers import upload_file, wait_for_resource


@pytest.fixture
def test_image_file(api_client, test_folder):
    file_path = f"{test_folder}/test_image.png"
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c6300010000050001a5f645400000000049454e44ae426082"
    )
    upload_file(api_client, file_path, png_bytes, content_type="image/png")
    yield file_path


@pytest.fixture
def test_folder_with_files(api_client, test_folder):
    for name in ("a_file.txt", "b_file.txt", "c_file.txt"):
        upload_file(
            api_client,
            f"{test_folder}/{name}",
            f"content of {name}",
        )
    yield test_folder


@pytest.fixture
def test_empty_folder(api_client):
    folder_path = f"app:/empty_folder_{uuid.uuid4().hex[:12]}"
    resp = api_client.put(
        f"{BASE_URL}/resources", params={"path": folder_path}
    )
    assert resp.status_code in (201, 409), resp.text
    assert wait_for_resource(api_client, folder_path)
    yield folder_path
    api_client.delete(
        f"{BASE_URL}/resources",
        params={"path": folder_path, "permanently": "true"},
    )


@pytest.fixture
def published_file(api_client, test_file_in_folder):
    resp = api_client.put(
        f"{BASE_URL}/resources/publish",
        params={"path": test_file_in_folder},
    )
    assert resp.status_code == 200, resp.text
    yield test_file_in_folder
    api_client.put(
        f"{BASE_URL}/resources/unpublish",
        params={"path": test_file_in_folder},
    )


@pytest.fixture
def unpublished_file(api_client, test_file_in_folder):
    yield test_file_in_folder
    api_client.put(
        f"{BASE_URL}/resources/unpublish",
        params={"path": test_file_in_folder},
    )