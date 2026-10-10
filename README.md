# Мактаб тестлари

Школьный тренажёр на Python 3.12 и Flask. Интерфейс на узбекском кириллицей, вопросы — на узбекской латинице, как в исходном документе. Режим тренажёра без таймера: неверный вариант отмечается, после верного ответа автоматически открывается следующий вопрос. Результат отражает ответы с первого раза. Проверка ответов выполняется на сервере.

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

Репозиторий: https://github.com/madsaomi/quizze. Ветка main, origin уже настроен.

```powershell
git add .
git commit -m "Add real question bank and subject icons"
git push origin main
```

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
- scripts/convert_docx.py, conversion_report.json — конвертер и отчёт по исходным данным.
- static/icons/ — SVG-иконки предметов.

Старый демонстрационный набор и PDF удалены. Исходный DOCX, виртуальное окружение, кэши и .env исключены из Git и Docker. В контейнер попадают только файлы приложения и рабочие JSON.

## Ограничения

Это тренажёр, а не защищённая экзаменационная система: API позволяет проверять варианты и выдаёт разбор после отправки, результаты не сохраняются. В рабочем наборе 4 680 вопросов по 13 предметам, извлечённых из DOCX. Ключ A сохранён согласно обозначению источника; варианты в интерфейсе перемешиваются. Исходный документ содержит повторы и неполные вопросы: подробности в conversion_report.json. Содержательная правильность ключей отдельно не проверялась.

## Большой набор вопросов

Данные валидируются и загружаются в память один раз при запуске процесса. API отдаёт по 20 вопросов (максимум 50) через offset/limit. Браузер асинхронно предзагружает следующую страницу, не скачивая весь банк. Проверка ответа использует индекс по ID. Gunicorn использует 2 процесса и по 4 потока; это конкурентное обслуживание Flask, не ASGI.

Конвертер конкретного исходного файла:

```powershell
.\.venv\Scripts\python.exe scripts/convert_docx.py 'Attestaciya jismoniy tarbiya.docx' data
```

Скрипт привязан к структуре данного документа; границы предметов заданы по параграфам. Для другого DOCX требуется адаптация. Исходный DOCX исключён из Git и контейнера. Демонстрационный JSON удалён. Скрипт проверяет SHA-256 исходного DOCX перед конвертацией.
