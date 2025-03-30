FROM python:3.12-slim

COPY requirements.txt .

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt --no-cache-dir

# Создаем рабочую директорию для приложения
WORKDIR /app

# Копируем исходный код
COPY src /app/src

# Настраиваем Python для поиска модулей
ENV PYTHONPATH=/app/src

# Запускаем приложение с 1 worker'ом
CMD ["gunicorn", "src.main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

#CMD gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000