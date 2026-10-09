# Мактаб тестлари

Школьный тренажёр на Python 3.12 и Flask. Интерфейс и вопросы на узбекском кириллицей. Вопросы по одному, 30 секунд на ответ, результат и разбор. Проверка ответов выполняется на сервере.

## Локальный запуск (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Открыть http://127.0.0.1:5000. Gunicorn устанавливается только на Linux/macOS; на Windows используется локальный Flask-сервер.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/app.js
```

GitHub Actions запускает тесты, проверку конфигурации Gunicorn, JavaScript и сборку Docker.

## GitHub

Репозиторий подготовлен локально. Привяжите нужный GitHub-репозиторий и выполните:

```powershell
git add .
git commit -m "Prepare school quiz app for Railway"
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin main
```

Замените OWNER/REPOSITORY своим адресом. Если origin уже существует, используйте `git remote set-url origin ...`. Не заменяйте содержимое существующего репозитория принудительным push без проверки его истории.

## Railway

1. Загрузить проект в GitHub.
2. В Railway выбрать New Project → Deploy from GitHub repo и нужный репозиторий.
3. Корневая папка сервиса: `/`. Dockerfile и railway.json находятся в корне. Отдельные Build Command и Start Command не нужны: команда запуска задана в Dockerfile.
4. Дождаться успешного деплоя и проверки `/health`.
5. В Settings → Networking создать публичный домен (Generate Domain).

Gunicorn слушает `0.0.0.0` и порт из `PORT`, который Railway задаёт автоматически. При локальном запуске контейнера порт по умолчанию 8000. Не задавайте вручную PORT без необходимости. Секреты и база данных сейчас не требуются. Необязательная переменная `WEB_CONCURRENCY` задаёт число процессов, по умолчанию 2.

```sh
docker build -t school-tests .
docker run --rm -p 8000:8000 school-tests
```

Проверка: http://localhost:8000/health возвращает `{"status":"ok"}`.

Конфигурация соответствует документации Railway:
- https://docs.railway.com/guides/flask
- https://docs.railway.com/config-as-code/reference
- https://docs.railway.com/deployments/healthchecks

## Структура

- app.py — HTTP-маршруты, защитные заголовки и healthcheck.
- quiz.py — загрузка/проверка данных и подсчёт баллов.
- data/ — JSON с вопросами и ключом ответов.
- templates/, static/ — интерфейс.
- tests/ — автоматические проверки.
- gunicorn.conf.py, Dockerfile, railway.json — production-запуск.
- AUDIT.md — результаты аудита и ограничения.

PDF и скачанный пример сохранены локально в .local/ и исключены из Git и Docker. Виртуальное окружение, кэши и .env также исключены. pypdf не нужен для работы сайта и удалён из зависимостей деплоя.

## Ограничения

Это тренажёр, а не защищённая экзаменационная система: таймер работает в браузере, API выдаёт разбор после отправки, результаты не сохраняются. В исходном наборе вопрос 12 имеет одинаковые варианты A/B; ответ 51 добавлен по смыслу. Добавляя тест, сохраните структуру data/jismoniy_tarbiya.json; приложение проверит данные при запуске.
