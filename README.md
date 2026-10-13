# Yandex Disk API Autotests

Проект автотестов для REST API Яндекс.Диска.

## О проекте

Автотесты покрывают публичное REST API Яндекс.Диска, документированное
по адресу https://yandex.ru/dev/disk/api/concepts/about-docpage/.
Базовый URL API: https://cloud-api.yandex.net.

Тесты проверяют работу методов GET, POST, PUT и DELETE на следующих
разделах API:

- /v1/disk
- /v1/disk/resources
- /v1/disk/resources/public
- /v1/disk/trash/resources
- /v1/disk/operations/{operation_id}

## Стек

- Python 3.10+
- pytest — фреймворк для тестов
- requests — HTTP-клиент

Дополнительные зависимости:

- python-dotenv — загрузка переменных окружения из .env

## Структура проекта

Каждый раздел API вынесен в отдельную подпапку. Внутри подпапки
файлы сгруппированы по HTTP-методам: test_<раздел>_get.py,
test_<раздел>_post.py, test_<раздел>_put.py, test_<раздел>_delete.py.

Фикстуры, специфичные для раздела, находятся в conftest.py этого
раздела. Общие фикстуры, используемые несколькими разделами, лежат в
корневом conftest.py. Вспомогательные функции (polling асинхронных
операций, загрузка файлов, поиск ресурсов в Корзине) собраны в
helpers.py.

## Установка и запуск

### 1. Клонирование репозитория

    git clone https://github.com/<username>/yandex-disk-api-tests.git
    cd yandex-disk-api-tests

### 2. Установка зависимостей

    pip install -r requirements.txt

### 3. Настройка переменных окружения

Создать файл .env в корне проекта:

    YANDEX_DISK_TOKEN=<ваш OAuth-токен>

### 4. Запуск всех тестов

    pytest

### 5. Запуск тестов конкретного раздела

    pytest tests/resources
    pytest tests/trash_resources
    pytest tests/public_resources

### 6. Запуск одного файла

    pytest tests/resources/test_resources_get.py -v

### 7. Запуск одного теста

    pytest tests/resources/test_resources_get.py::TestGetResourceMetadata::test_folder_returns_directory_metadata -v

## Конфигурация

Файл pytest.ini задаёт корневую папку для поиска тестов и формат
вывода:

    [pytest]
    testpaths = tests
    python_files = test_*.py
    python_classes = Test*
    python_functions = test_*
    addopts = -v --tb=short

## Принципы построения тестов

- Тесты сгруппированы по разделам API и HTTP-методам.
- Внутри раздела каждый эндпоинт покрыт отдельным классом тестов.
- Каждый тест создаёт собственные ресурсы через фикстуры и очищает
  их после завершения. Это обеспечивает независимость тестов друг
  от друга и возможность запуска в любом порядке.
- Коды успешных ответов проверяются строго: 200, 201, 202, 204 в
  зависимости от эндпоинта.
- Проверка ошибок выполняется как минимум на один сценарий для
  каждого эндпоинта: несуществующий путь, отсутствующий обязательный
  параметр, конфликт имени ресурса.

