import uuid

import pytest

from config import BASE_URL
from helpers import (
    delete_to_trash,
    find_in_trash,
    upload_file,
    wait_for_resource,
)


@pytest.fixture
def trashed_file(api_client):
    name = f"trash_file_{uuid.uuid4().hex[:8]}.txt"
    upload_file(api_client, f"app:/{name}", "trash file content")
    delete_to_trash(api_client, f"app:/{name}")

    trash_path = find_in_trash(api_client, name)
    assert trash_path, f"Файл {name} не найден в Корзине"

    yield trash_path

    api_client.delete(
        f"{BASE_URL}/trash/resources",
        params={"path": trash_path, "permanently": "true"},
    )


@pytest.fixture
def trashed_folder(api_client):
    name = f"trash_folder_{uuid.uuid4().hex[:8]}"
    api_client.put(f"{BASE_URL}/resources", params={"path": f"app:/{name}"})
    assert wait_for_resource(api_client, f"app:/{name}")
    delete_to_trash(api_client, f"app:/{name}")

    trash_path = find_in_trash(api_client, name)
    assert trash_path, f"Папка {name} не найдена в Корзине"

    yield trash_path

    api_client.delete(
        f"{BASE_URL}/trash/resources",
        params={"path": trash_path, "permanently": "true"},
    )


@pytest.fixture
def trashed_files(api_client):
    names = [
        f"trash_multi_{uuid.uuid4().hex[:8]}_{i}.txt" for i in range(3)
    ]
    for i, name in enumerate(names):
        upload_file(api_client, f"app:/{name}", f"content {i}")
        delete_to_trash(api_client, f"app:/{name}")

    paths = []
    for name in names:
        trash_path = find_in_trash(api_client, name)
        assert trash_path, f"Файл {name} не найден в Корзине"
        paths.append(trash_path)

    yield paths

    for trash_path in paths:
        api_client.delete(
            f"{BASE_URL}/trash/resources",
            params={"path": trash_path, "permanently": "true"},
        )


@pytest.fixture
def restorable_file(api_client):
    name = f"restorable_{uuid.uuid4().hex[:8]}.txt"
    original = f"app:/{name}"
    upload_file(api_client, original, "to restore")
    delete_to_trash(api_client, original)

    trash_path = find_in_trash(api_client, name)
    assert trash_path, f"Файл {name} не найден в Корзине"

    state = {
        "name": name,
        "original": original,
        "trash_path": trash_path,
        "cleanup_paths": [],
    }
    yield state

    for p in [original, trash_path] + state["cleanup_paths"]:
        api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": p, "permanently": "true"},
        )
        api_client.delete(
            f"{BASE_URL}/trash/resources",
            params={"path": p, "permanently": "true"},
        )


@pytest.fixture
def restorable_folder(api_client):
    name = f"restorable_folder_{uuid.uuid4().hex[:8]}"
    original = f"app:/{name}"
    api_client.put(f"{BASE_URL}/resources", params={"path": original})
    assert wait_for_resource(api_client, original)
    delete_to_trash(api_client, original)

    trash_path = find_in_trash(api_client, name)
    assert trash_path, f"Папка {name} не найдена в Корзине"

    state = {
        "name": name,
        "original": original,
        "trash_path": trash_path,
        "cleanup_paths": [],
    }
    yield state

    for p in [original, trash_path] + state["cleanup_paths"]:
        api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": p, "permanently": "true"},
        )
        api_client.delete(
            f"{BASE_URL}/trash/resources",
            params={"path": p, "permanently": "true"},
        )