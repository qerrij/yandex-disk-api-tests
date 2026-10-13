import pytest

from config import BASE_URL
from helpers import resource_exists, start_async_copy


@pytest.fixture
def running_operation(api_client, test_non_empty_folder, test_folder):
    dst = f"{test_folder}/op_result"
    operation_id = start_async_copy(
        api_client, test_non_empty_folder, dst
    )

    yield {"id": operation_id, "dst": dst}

    if resource_exists(api_client, dst):
        api_client.delete(
            f"{BASE_URL}/resources",
            params={"path": dst, "permanently": "true"},
        )