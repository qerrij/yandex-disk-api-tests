import pytest

from config import BASE_URL


class TestGetDiskInfo:
    """Тесты GET /v1/disk — информация о Диске."""

    def test_response_contains_disk_capacity_metrics(self, api_client):
        """Плоский ответ содержит числовые метрики объёма:
        total_space, used_space, trash_size — неотрицательные числа,
        total_space > 0."""
        response = api_client.get(f"{BASE_URL}/")
        assert response.status_code == 200, response.text
        data = response.json()

        for key in ("total_space", "used_space", "trash_size"):
            assert key in data, f"Отсутствует поле {key}"
            assert isinstance(data[key], int), \
                f"{key} должен быть числом, получено {type(data[key]).__name__}"
            assert data[key] >= 0, f"{key} отрицательный: {data[key]}"

        assert data["total_space"] > 0, "total_space должен быть больше нуля"

    def test_response_contains_user_and_system_folders_blocks(self, api_client):
        """Вложенные блоки user и system_folders присутствуют
        и содержат ключевые поля с валидными значениями."""
        response = api_client.get(f"{BASE_URL}/")
        assert response.status_code == 200, response.text
        data = response.json()

        assert "user" in data, "Отсутствует блок user"
        assert data["user"].get("uid"), "user.uid пустой"

        assert "system_folders" in data, "Отсутствует блок system_folders"
        folders = data["system_folders"]
        assert "downloads" in folders, "system_folders.downloads отсутствует"
        assert "applications" in folders, "system_folders.applications отсутствует"
        assert folders["downloads"].startswith("disk:/"), \
            f"downloads имеет неожиданный путь: {folders['downloads']}"
        assert folders["applications"].startswith("disk:/"), \
            f"applications имеет неожиданный путь: {folders['applications']}"

    def test_fields_param_returns_only_requested_attributes(self, api_client):
        """Параметр fields сужает ответ до перечисленных ключей."""
        response = api_client.get(
            f"{BASE_URL}/", params={"fields": "total_space,used_space"}
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert set(data.keys()) == {"total_space", "used_space"}, \
            f"fields не отфильтровал ответ: {set(data.keys())}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])