# Сервис сокращения ссылок

Сервис позволяет пользователям сокращать длинные URL-адреса, управлять ими, просматривать статистику и объединять ссылки в проекты.

## Описание API

### Управление ссылками
| Метод | Эндпоинт | Описание | Аутентификация |
|-------|----------|----------|----------------|
| GET | /{short_code} | Перенаправление на оригинальный URL | Опционально |
| POST | /api/v1/links/shorten | Создание короткой ссылки | Опционально |
| PUT | /api/v1/links/{short_code} | Обновление ссылки | Да |
| DELETE | /api/v1/links/{short_code} | Удаление ссылки | Да |
| GET | /api/v1/links/{short_code}/stats | Получение статистики по ссылке | Опционально |
| GET | /api/v1/links/search | Поиск ссылок по оригинальному URL | Да |
| GET | /api/v1/links/popular | Показ популярных ссылок (по числу кликов) | Нет

### Управление проектами
| Метод | Эндпоинт | Описание | Аутентификация |
|-------|----------|----------|----------------|
| GET | /api/v1/projects | Получение списка проектов пользователя | Да |
| POST | /api/v1/projects | Создание нового проекта | Да |
| GET | /api/v1/projects/public | Получение информации о "публичном" проекте | Нет |
| GET | /api/v1/projects/{project_id} | Получение информации о проекте | Да |
| PUT | /api/v1/projects/{project_id} | Обновление проекта | Да (только админ проекта) |
| DELETE | /api/v1/projects/{project_id} | Удаление проекта | Да (только админ проекта) |
| POST | /api/v1/projects/{project_id}/members | Добавление пользователя в проект | Да (только админ) |
| DELETE | /api/v1/projects/{project_id}/users/{user_id} | Удаление пользователя из проекта | Да (только админ) |

### Особенности реализации
- Неавторизованные пользователи могут создавать ссылки в публичном проекте с ограниченным сроком жизни (5 дней, задается в конфиге)
- Авторизованные пользователи могут управлять своими ссылками и проектами
- При регистрации пользователя создается его "личный" проект
- У проекта может быть несколько администраторов (по умолчанию - создатель проекта)
- Для проекта задается время жизни ссылок по умолчанию (в днях, умолчание - в конфиге)
- Реализовано кэширование популярных ссылок и статистики в Redis
- Автоматическая очистка истекших ссылок с помощью планировщика задач

## Примеры запросов

**Создание короткой ссылки**
```bash
curl -X POST "http://localhost:8000/api/v1/links/shorten" \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://example.com/very/long/path", "short_code": "example", "expires_at": "2025-12-31T23:59:59", "project_id": 1, "is_public": true}'
```
Параметры:
- `original_url` - обязательный, исходный URL
- `custom_alias` - опциональный, пользовательский алиас
- `expires_at` - опциональный, дата истечения ссылки
- `project_id` - опциональный, ID проекта (для авторизованных пользователей)

**Создание короткой ссылки анонимным пользователем.** 
```bash
curl -X POST "http://localhost:8000/api/v1/links/shorten" \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://example.com/very/long/path"}'
```
Требуется минимальный набор параметров, в результате - автогенерация короткого кода, публичная ссылка и срок жизни по-умолчанию для публичного проекта.

**Создание нового проекта**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/projects' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "string",
  "description": "string",
  "default_link_lifetime_days": 30
}'
```

**Добавление пользователя в проект**
```bash
curl -X POST "http://localhost:8000/api/v1/projects/1/members" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"email": "user@example.com", "is_admin": false}'
```

**Получение статистики**
```bash
curl -X GET "http://localhost:8000/api/v1/links/example/stats"
```
Для публичных ссылок не требует аутентификации. Для приватных ссылок требуется быть владельцем или участником проекта.

Ответ:
```json
{
  "original_url": "https://example.com/",
  "short_code": "string",
  "expires_at": "2025-05-31T01:46:41.061Z",
  "clicks_count": 12,
  "last_clicked_at": "2025-03-31T01:46:41.061Z"
}
```

**Поиск ссылки по оригинальному URL**
```bash
curl -X GET "http://localhost:8000/api/v1/links/search?original_url=https://example.com/very/long/path" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Инструкция по запуску

### Предварительные требования

- Docker и Docker Compose
- Доступ к интернету для скачивания образов

### Подготовка

1. Клонируйте репозиторий
2. Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

3. Отредактируйте `.env` файл, указав необходимые настройки:

```env
# Database settings
DB_USER=postgres
DB_PASS=password
DB_HOST=db
DB_PORT=5432
DB_NAME=link_shortener
DB_INIT=true
DB_ECHO=false

# Redis settings
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_password
REDIS_SSL=false
REDIS_DB=0

# FastAPI settings
SECRET=your-secret-key

# CORS settings
CORS_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000"]
CORS_HEADERS=["*"]
CORS_METHODS=["*"]
CORS_CREDENTIALS=true

SCHEDULER_CLEANUP_INTERVAL=2  # минуты

LOG_LEVEL=INFO
```

### Запуск с помощью Docker Compose

```bash
docker-compose up -d
```

Сервис будет доступен по адресу: http://localhost:80

### Проверка работоспособности

```bash
curl http://localhost:80/docs
```

## Описание БД

### PostgreSQL

Основное хранилище данных с таблицами:

- **users** - информация о пользователях
  - id, email, пароль и другие данные пользователя

- **projects** - группировка ссылок
  - id, название, описание, владелец, дата создания
  - каждый проект принадлежит одному или нескольким пользователям
  - для проекта задается срок жизни ссылок по умолчанию
  - особый проект "Public" для неавторизованных пользователей

- **links** - короткие ссылки
  - id, короткий код, оригинальный URL, дата создания
  - связь с проектом и пользователем-создателем
  - статистика использования (счетчик кликов, дата последнего использования)
  - срок жизни ссылки (expires_at)

- **project_users** - связь many:many между проектами и пользователями
  - id проекта, id пользователя, роль пользователя в проекте (is_admin)

### Redis

Используется для кэширования:
- Прав доступа к ссылкам (ключ составной - ссылка+пользователь, TTL: 5 минут)
- Всех использованных ссылок (TTL: 1 час)
- Статистики по ссылкам (TTL: 1 час)
- Популярных ссылок (TTL: 10 минут)

Раздельно кешируется "статическая" информация о ссылке и "динамическая" (это только число кликов и время последнего клика)

Кэш автоматически инвалидируется при:
- Обновлении статистики (клики)
- Очистке истекших ссылок
- Обновлении/удалении ссылок

## ER-диаграмма

```mermaid
erDiagram
    USERS {
        uuid id PK
        string email
        string hashed_password
        bool is_active
        bool is_superuser "не используется"
        bool is_verified "не используется"
    }
    
    PROJECTS {
        int id PK
        string name
        int default_link_lifetime_days "время жизни по-умолчанию"
        datetime created_at
        int owner_id FK
    }
    
    LINKS {
        int id PK
        string original_url
        string short_code UK
        datetime created_at
        datetime expires_at
        int owner_id FK
        int project_id FK
        int clicks_count
        datetime last_clicked_at
        bool is_public
    }
    
    PROJECT_MEMBERS {
        int project_id PK,FK
        int user_id PK,FK
        bool is_admin
        datetime joined_at
    }
    
    USERS ||--o{ PROJECTS : "создает"
    USERS ||--o{ LINKS : "создает"
    PROJECTS ||--o{ LINKS : "содержит"
    PROJECTS ||--o{ PROJECT_MEMBERS : "включает"
    USERS ||--o{ PROJECT_MEMBERS : "участвует в"