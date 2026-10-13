import time

import requests

from config import BASE_URL


def wait_for_resource(api_client, path, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = api_client.get(f"{BASE_URL}/resources", params={"path": path})
        if resp.status_code == 200:
            return True
        time.sleep(0.5)
    return False


def wait_for_operation(api_client, operation_href, timeout=60, interval=1.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = api_client.get(operation_href)
        if resp.status_code != 200:
            time.sleep(interval)
            continue
        data = resp.json()
        status = data.get("status")
        if status == "success":
            return data
        if status == "failed":
            raise AssertionError(f"Операция завершилась с ошибкой: {data}")
        time.sleep(interval)
    raise AssertionError(
        f"Операция не завершилась за {timeout} сек: {operation_href}"
    )


def resource_exists(api_client, path):
    resp = api_client.get(f"{BASE_URL}/resources", params={"path": path})
    return resp.status_code == 200


def get_upload_url(api_client, path, max_attempts=5):
    last_resp = None
    for _ in range(max_attempts):
        resp = api_client.get(
            f"{BASE_URL}/resources/upload",
            params={"path": path, "overwrite": "true"},
        )
        last_resp = resp
        if resp.status_code == 200:
            return resp.json()["href"]
        time.sleep(1)
    raise AssertionError(
        f"Не удалось получить upload URL для {path}: "
        f"{last_resp.status_code} {last_resp.text}"
    )


def upload_file(api_client, path, content, content_type="text/plain"):
    href = get_upload_url(api_client, path)
    resp = requests.put(
        href, data=content, headers={"Content-Type": content_type}
    )
    assert resp.status_code == 201, resp.text


def find_in_trash(api_client, name, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = api_client.get(
            f"{BASE_URL}/trash/resources",
            params={"path": "/", "limit": 200, "sort": "-deleted"},
        )
        if resp.status_code == 200:
            items = resp.json().get("_embedded", {}).get("items", [])
            for item in items:
                if item.get("name") == name:
                    return item["path"]
        time.sleep(0.5)
    return None


def delete_to_trash(api_client, path):

    resp = api_client.delete(f"{BASE_URL}/resources", params={"path": path})
    assert resp.status_code == 204, \
        f"Не удалось удалить {path} в Корзину: {resp.status_code} {resp.text}"


def start_async_copy(api_client, src, dst):

    response = api_client.post(
        f"{BASE_URL}/resources/copy",
        params={"from": src, "path": dst},
    )
    assert response.status_code == 202, \
        f"Ожидали 202 для async-копии: {response.status_code} {response.text}"

    href = response.json()["href"]
    return href.rstrip("/").rsplit("/", 1)[-1]