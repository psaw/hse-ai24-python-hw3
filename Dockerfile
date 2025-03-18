FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Установка uv
RUN pip install uv

# Копирование файлов проекта
COPY pyproject.toml .
COPY src src/

# Установка зависимостей
RUN uv venv && . .venv/bin/activate && uv pip install -e .

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 