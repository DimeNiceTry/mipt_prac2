Лаба 2. Docker
оба docker #1 и #2 хранятся тут

Небольшое приложение с заметками на FastAPI. Можно добавить заметку и посмотреть
список сохранённых. Код лежит в app/main.py. Оба задания сделаны на одном приложении:
сначала отдельный контейнер, потом Nginx, приложение и PostgreSQL через compose.

Понадобятся свободные порты 80 и 8080 и пайтон.

Команды ниже для PowerShell.
Выполнять всё из папки проекта.

**Запуск через compose**

На другой машине сначала скачать ветку с лабой:

    git clone --branch lab2 https://github.com/DimeNiceTry/mipt_prac2.git
    cd mipt_prac2

Дальше скопировать настройки:

    Copy-Item .env.example .env

В .env заменить значение POSTGRES_PASSWORD своим паролем. Если .env уже есть,
заново копировать его не нужно. Настоящий .env не попадает в git и в сборку образа,
в репозитории только пример настроек.

    docker compose up -d
    docker compose ps
    curl.exe -i http://localhost/health

При первом запуске образ приложения соберётся сам. Нужо подождать,
пока все три контейнера станут healthy. Можно сразу запускать с ожиданием:

    docker compose up -d --wait

Приложение открывается на http://localhost, документация с кнопками для запросов -
на http://localhost/docs. У /health должен быть ответ 200 и {"status":"ok"}.

Снаружи доступен только Nginx на 80 порту. С Nginx приложение связано через frontend,
с PostgreSQL через backend. У базы только backend, эта сеть внутренняя.
Данные лежат в томе pgdata. Само приложение запускается от пользователя 10001,
файловая система у него только для чтения, кроме временной папки /tmp.

Compose выдаёт предупреждение про version 3.8. Поле оставлено по условию задания,
на запуск это не влияет.

Отдельный контейнер, для первой части

    docker build -t lab2:local .
    docker run -d --rm --name lab2-standalone -p 8080:8080 -e "APP_NAME=Lab 2 standalone" lab2:local
    curl.exe -i http://localhost:8080/health

Тут тоже должен быть HTTP 200. Документация будет на http://localhost:8080/docs.
Если не задан DB_HOST, приложение работает с SQLite внутри контейнера, поэтому
для этой проверки отдельно поднимать PostgreSQL не нужно. В таком режиме данные
удаляются вместе с контейнером.

Посмотреть статус и пользователя:

    docker ps --filter name=lab2-standalone
    docker exec lab2-standalone id

В Dockerfile два этапа: builder ставит зависимости, runtime получает готовое
окружение и приложение. Runtime на Python slim, запуск от non-root.
Версии образов закреплены вместе с digest, зависимости Python - с версиями
и хешами в requirements.txt.

Остановить отдельный контейнер:

    docker stop lab2-standalone

Проверка заметок и базы

В http://localhost/docs открыть POST /notes и отправить, например,
{"text":"первая заметка"}. Потом через GET /notes посмотреть, что она сохранилась.
Пустой текст и текст длиннее 1000 символов вернут 422. /health проверяет ещё
и соединение с базой: если она недоступна, вернётся 503.

Есть скрипт, который проверяет запросы, статусы контейнеров, порты и пользователя:

    python scripts/verify.py

Чтобы заодно проверить сохранность данных:

    python scripts/verify.py --recreate

Скрипт добавит заметку, пересоздаст контейнеры без удаления тома и проверит,
что заметка осталась. Вывод выполненной проверки - [тут](docs/verification.txt).

Обычная остановка и повторный запуск:

    docker compose down
    docker compose up -d
    
Ещё момент

пароль в .env используется при создании базы. Если том уже существует,
простая замена пароля в файле не поменяет пароль внутри PostgreSQL.

Выгрузка образа

    docker login ghcr.io -u DimeNiceTry
    python scripts/publish.py

При входе в GHCR вместо пароля вводится токен с правами на публикацию образов.
В файлы проекта его записывать не надо. Скрипт собирает образ и отправляет
ghcr.io/dimenicetry/mipt_prac2:lab2. Для другого registry или тега:

    python scripts/publish.py --image registry.example.com/user/notes --tag lab2

Для обычного запуска через compose вход в GHCR не нужен, всё собирается из исходников.

Скрины лежат в docs/screenshots:

- [отдельный контейнер](docs/screenshots/standalone.png)
- [контейнеры compose](docs/screenshots/containers.png)
- [проверка сохранения данных](docs/screenshots/verification.png)
- [API](docs/screenshots/api.png)

На первых трёх - PowerShell с проверками, на последнем - запрос и ответ в Swagger UI.
