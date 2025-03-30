FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Установка системных зависимостей, включая postgresql-client
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в рабочую директорию
# Это включает src, alembic.ini, migrations/, entrypoint.sh и т.д.
COPY . .

# Настраиваем Python для поиска модулей
ENV PYTHONPATH=/app

# Делаем entrypoint.sh исполняемым
RUN chmod +x /app/entrypoint.sh

# Устанавливаем entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Команда по умолчанию (будет передана как аргументы в entrypoint.sh)
CMD ["gunicorn", "src.main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

#CMD gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000