import uuid

import pytest
import requests

from config import BASE_URL, TOKEN
from helpers import wait_for_resource, upload_file



@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({
        "Authorization": f"OAuth {TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    return session


@pytest.fixture(scope="session")
def anonymous_client():
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    return session


@pytest.fixture(scope="session")
def external_file_url():
    return "https://raw.githubusercontent.com/psf/requests/main/LICENSE"



@pytest.fixture
def test_folder(api_client):
    folder_path = f"app:/test_folder_{uuid.uuid4().hex[:12]}"
    resp = api_client.put(
        f"{BASE_URL}/resources", params={"path": folder_path}
    )
    assert resp.status_code in (201, 409), resp.text
    assert wait_for_resource(api_client, folder_path), \
        f"Папка {folder_path} не появилась"
    yield folder_path
    api_client.delete(
        f"{BASE_URL}/resources",
        params={"path": folder_path, "permanently": "true"},
    )


@pytest.fixture
def test_file_in_folder(api_client, test_folder):
    file_path = f"{test_folder}/test_file.txt"
    upload_file(api_client, file_path, "Hello, Yandex Disk!")
    yield file_path


@pytest.fixture
def test_non_empty_folder(api_client):
    folder_path = f"app:/non_empty_src_{uuid.uuid4().hex[:12]}"
    resp = api_client.put(
        f"{BASE_URL}/resources", params={"path": folder_path}
    )
    assert resp.status_code in (201, 409), resp.text
    assert wait_for_resource(api_client, folder_path), \
        f"Папка {folder_path} не появилась"

    for name in ("a_file.txt", "b_file.txt"):
        upload_file(
            api_client,
            f"{folder_path}/{name}",
            f"content of {name}",
        )

    yield folder_path
    api_client.delete(
        f"{BASE_URL}/resources",
        params={"path": folder_path, "permanently": "true"},
    )