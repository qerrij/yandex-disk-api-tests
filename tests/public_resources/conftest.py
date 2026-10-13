import uuid

import pytest

from config import BASE_URL
from helpers import upload_file, wait_for_resource


@pytest.fixture
def published_file_meta(api_client, test_file_in_folder):
    publish_resp = api_client.put(
        f"{BASE_URL}/resources/publish",
        params={"path": test_file_in_folder},
    )
    assert publish_resp.status_code == 200, \
        f"Publish failed: {publish_resp.status_code} {publish_resp.text}"

    meta = api_client.get(
        f"{BASE_URL}/resources", params={"path": test_file_in_folder}
    ).json()
    assert "public_key" in meta and "public_url" in meta, \
        f"Ожидались public_key и public_url: {meta}"

    yield meta

    api_client.put(
        f"{BASE_URL}/resources/unpublish",
        params={"path": test_file_in_folder},
    )


@pytest.fixture
def published_folder_meta(api_client):
    folder = f"app:/public_folder_{uuid.uuid4().hex[:12]}"
    api_client.put(f"{BASE_URL}/resources", params={"path": folder})
    assert wait_for_resource(api_client, folder)

    for name in ("a.txt", "b.txt"):
        upload_file(api_client, f"{folder}/{name}", f"content of {name}")

    publish_resp = api_client.put(
        f"{BASE_URL}/resources/publish", params={"path": folder}
    )
    assert publish_resp.status_code == 200, \
        f"Publish failed: {publish_resp.status_code} {publish_resp.text}"

    meta = api_client.get(
        f"{BASE_URL}/resources", params={"path": folder}
    ).json()
    assert "public_key" in meta and "public_url" in meta, \
        f"Ожидались public_key и public_url: {meta}"

    yield {**meta, "disk_path": folder}

    api_client.delete(
        f"{BASE_URL}/resources",
        params={"path": folder, "permanently": "true"},
    )