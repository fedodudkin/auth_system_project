# Auth & RBAC System

> Кастомная система аутентификации и ролевого управления доступом на Django REST Framework — без использования `django.contrib.auth`.

---

## Содержание

- [Обзор проекта](#обзор-проекта)
- [Технологический стек](#технологический-стек)
- [Архитектура RBAC](#архитектура-rbac)
- [Структура проекта](#структура-проекта)
- [Установка и запуск](#установка-и-запуск)
- [Запуск через Docker](#запуск-через-docker)
- [API Endpoints](#api-endpoints)
- [Тестирование](#тестирование)

---

## Обзор проекта

Проект реализует полноценную систему аутентификации и авторизации с нуля:

- **Аутентификация** — JWT-токены (PyJWT) + хэширование паролей через bcrypt
- **Авторизация** — RBAC (Role-Based Access Control) на основе трёх таблиц
- **Middleware** — автоматическое извлечение пользователя из заголовка `Authorization: Bearer <token>` и прикрепление к `request.my_user`
- **Soft Delete** — деактивация пользователя (`is_active=False`) вместо физического удаления
- **Admin API** — полный CRUD для управления правилами доступа через API
- **Rate Limiting** — защита эндпоинтов входа и регистрации от брутфорса
- **Swagger UI** — интерактивная документация API через drf-spectacular
- **Docker** — полная контейнеризация приложения и базы данных

Стандартные механизмы Django (`AbstractUser`, `django.contrib.auth`, сессии) намеренно не используются.

---

## Технологический стек

| Компонент          | Технология              |
|--------------------|-------------------------|
| Фреймворк          | Django 5.x              |
| REST API           | Django REST Framework   |
| База данных        | PostgreSQL              |
| Аутентификация     | PyJWT 2.x               |
| Хэширование        | bcrypt                  |
| Документация API   | drf-spectacular         |
| Rate Limiting      | django-ratelimit        |
| Контейнеризация    | Docker, docker-compose  |
| Переменные среды   | python-dotenv           |

---

## Архитектура RBAC

Система прав доступа построена на трёх таблицах:

```
Role ──────────────────┐
                       ▼
BusinessElement ──► AccessRoleRule
```

### Таблицы

**`Role`** — роль пользователя в системе:
```
Admin | Manager | User
```

**`BusinessElement`** — защищаемый ресурс:
```
Products | Users | Orders | Roles | AccessRules
```

**`AccessRoleRule`** — матрица прав: какая роль что может делать с каким ресурсом:

| Поле         | Описание                               |
|--------------|----------------------------------------|
| `read`       | Читать **свой** объект                 |
| `read_all`   | Читать **все** объекты                 |
| `create`     | Создавать объекты                      |
| `update`     | Редактировать **свой** объект          |
| `update_all` | Редактировать **любой** объект         |
| `delete`     | Удалять **свой** объект                |
| `delete_all` | Удалять **любой** объект               |

### Разница между `read` и `read_all`

- `read=True` — пользователь видит только **собственные** ресурсы (ownership check на уровне view)
- `read_all=True` — пользователь видит **все** ресурсы без ограничений

Это разделение применяется ко всем парным правам: `update/update_all`, `delete/delete_all`.

### Матрица прав по умолчанию (seed_db)

| Роль    | read | read_all | create | update | update_all | delete | delete_all |
|---------|------|----------|--------|--------|------------|--------|------------|
| Admin   | ✅   | ✅       | ✅     | ✅     | ✅         | ✅     | ✅         |
| Manager | ✅   | ✅       | ✅     | ✅     | ✅         | ❌     | ❌         |
| User    | ✅   | ❌       | ✅     | ✅     | ❌         | ❌     | ❌         |

> Admin получает полный доступ ко всем бизнес-элементам, включая управление ролями и правилами доступа.

---

## Структура проекта

```
auth_system_project/
├── core/                            # Настройки проекта
│   ├── __init__.py
│   ├── settings.py
│   ├── settings_test.py             # Настройки для тестового окружения
│   ├── exceptions.py                # Обработчик ошибок rate limiting (429)
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── __init__.py
│   │
│   ├── users/                       # Управление пользователями
│   │   ├── __init__.py
│   │   ├── models.py                # Модель User
│   │   ├── serializers.py           # Register / Login / Profile / Update
│   │   ├── services.py              # bcrypt + PyJWT утилиты
│   │   ├── views.py                 # Register, Login, Logout, Profile, SoftDelete
│   │   ├── urls.py
│   │   └── tests.py
│   │
│   ├── access/                      # Аутентификация и авторизация
│   │   ├── __init__.py
│   │   ├── models.py                # Role, BusinessElement, AccessRoleRule
│   │   ├── serializers.py           # AccessRoleRule CRUD сериализаторы
│   │   ├── views.py                 # RoleList, AccessRuleList, AccessRuleDetail
│   │   ├── middleware.py            # JWTAuthMiddleware
│   │   ├── permissions.py           # RBACPermission, @require_permission
│   │   ├── urls.py
│   │   └── management/
│   │       ├── __init__.py
│   │       └── commands/
│   │           ├── __init__.py
│   │           └── seed_db.py       # Инициализация ролей и прав
│   │
│   └── business/                    # Тестовые бизнес-объекты
│       ├── __init__.py
│       ├── views.py                 # Mock: Products, Orders
│       ├── urls.py
│       └── tests.py
│
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env                             # Переменные среды (не коммитить!)
├── .env.example                     # Шаблон переменных среды
├── .gitignore
├── requirements.txt
└── manage.py
```

---

## Установка и запуск

### Локальный запуск (без Docker)

#### 1. Клонировать репозиторий

```bash
git clone <repository-url>
cd auth_system_project
```

#### 2. Создать и активировать виртуальное окружение

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

#### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

#### 4. Настроить переменные среды

```bash
cp .env.example .env
```

Открыть `.env` и заполнить значения:

```env
# Django
SECRET_KEY=your-secret-django-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT
JWT_SECRET=your-secret-jwt-key
JWT_EXPIRATION_HOURS=24

# PostgreSQL
DB_NAME=auth_db
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost     # для локального запуска
DB_PORT=5432
```

#### 5. Создать базу данных PostgreSQL

```sql
CREATE DATABASE auth_db;
```

#### 6. Применить миграции

```bash
python manage.py migrate
```

#### 7. ⚠️ Обязательно: инициализировать роли и права

```bash
python manage.py seed_db
```

Команда создаёт роли (`Admin`, `Manager`, `User`), бизнес-элементы и матрицу прав доступа. **Без этого шага авторизация работать не будет.**

Команда идемпотентна — её можно запускать повторно без риска дублирования данных.

#### 8. Запустить сервер

```bash
python manage.py runserver
```

---

## Запуск через Docker

#### 1. Настроить переменные среды

```bash
cp .env.example .env
```

В `.env` указать `DB_HOST=db` (имя сервиса из docker-compose):

```env
DB_HOST=db     # ← для Docker, не localhost
```

#### 2. Собрать и запустить контейнеры

```bash
docker-compose up --build
```

При первом запуске автоматически выполнятся:
- `python manage.py migrate`
- `python manage.py seed_db`

#### 3. Последующие запуски

```bash
# В фоне
docker-compose up -d

# Остановить
docker-compose down

# Остановить и удалить данные БД
docker-compose down -v
```

API доступно по адресу: `http://127.0.0.1:8000/`

---

## API Endpoints

### Формат авторизации

Все защищённые эндпоинты требуют заголовок:

```
Authorization: Bearer <jwt_token>
```

### Swagger UI

Интерактивная документация доступна после запуска сервера:

```
http://127.0.0.1:8000/api/schema/swagger-ui/
```

---

### Пользователи `/api/users/`

| Метод    | URL                      | Доступ           | Rate Limit | Описание                        |
|----------|--------------------------|------------------|------------|---------------------------------|
| `POST`   | `/api/users/register/`   | Публичный        | 3 / 10 мин | Регистрация нового пользователя |
| `POST`   | `/api/users/login/`      | Публичный        | 5 / мин    | Вход, возвращает JWT-токен      |
| `POST`   | `/api/users/logout/`     | Аутентифицирован | —          | Выход из системы                |
| `GET`    | `/api/users/profile/`    | Аутентифицирован | —          | Просмотр своего профиля         |
| `PATCH`  | `/api/users/profile/`    | Аутентифицирован | —          | Обновление профиля              |
| `DELETE` | `/api/users/me/`         | Аутентифицирован | —          | Мягкое удаление аккаунта        |

**Пример: регистрация**
```json
POST /api/users/register/
{
    "name": "Иван Иванов",
    "email": "ivan@example.com",
    "password": "securepass123",
    "password_confirmation": "securepass123"
}
```

**Пример: логин**
```json
POST /api/users/login/
{
    "email": "ivan@example.com",
    "password": "securepass123"
}
```

---

### Управление доступом `/api/access/`

| Метод    | URL                          | Права                      | Описание                    |
|----------|------------------------------|----------------------------|-----------------------------|
| `GET`    | `/api/access/roles/`         | `Roles → read_all`         | Список всех ролей           |
| `GET`    | `/api/access/rules/`         | `AccessRules → read_all`   | Список всех правил доступа  |
| `POST`   | `/api/access/rules/`         | `AccessRules → create`     | Создать новое правило       |
| `GET`    | `/api/access/rules/<id>/`    | `AccessRules → read`       | Детали правила              |
| `PATCH`  | `/api/access/rules/<id>/`    | `AccessRules → update_all` | Изменить права              |
| `DELETE` | `/api/access/rules/<id>/`    | `AccessRules → delete_all` | Удалить правило             |

**Пример: изменить права роли**
```json
PATCH /api/access/rules/3/
Authorization: Bearer <admin_token>

{
    "read_all": true,
    "delete": false,
    "delete_all": false
}
```

---

### Бизнес-объекты `/api/business/` (демонстрация RBAC)

| Метод    | URL                              | Права                    | Описание            |
|----------|----------------------------------|--------------------------|---------------------|
| `GET`    | `/api/business/products/`        | `Products → read_all`    | Список продуктов    |
| `GET`    | `/api/business/products/<id>/`   | `Products → read`        | Детали продукта     |
| `PUT`    | `/api/business/products/<id>/`   | `Products → update_all`  | Обновление продукта |
| `DELETE` | `/api/business/products/<id>/`   | `Products → delete_all`  | Удаление продукта   |
| `GET`    | `/api/business/orders/`          | `Orders → read_all`      | Список заказов      |

---

### Коды ответов

| Код  | Описание                                              |
|------|-------------------------------------------------------|
| 200  | Успешный запрос                                       |
| 201  | Ресурс создан                                         |
| 400  | Ошибка валидации данных                               |
| 401  | Не аутентифицирован (токен отсутствует или истёк)     |
| 403  | Доступ запрещён (недостаточно прав)                   |
| 404  | Ресурс не найден                                      |
| 429  | Слишком много запросов (rate limit превышен)          |

---

## Тестирование

Rate limiting отключается автоматически через отдельный файл настроек `core/settings_test.py`.

### Запустить все тесты

```bash
python manage.py test --settings=core.settings_test -v 2
```

### Запустить тесты по модулям

```bash
# Тесты аутентификации
python manage.py test apps.users.tests --settings=core.settings_test

# Тесты RBAC
python manage.py test apps.business.tests --settings=core.settings_test
```

### Покрытие тестами

| Класс                   | Что тестируется                                                          |
|-------------------------|--------------------------------------------------------------------------|
| `RegistrationTests`     | Создание пользователя, хэширование пароля, совпадение паролей, валидация |
| `LoginTests`            | Аутентификация, генерация токена, неверные credentials                   |
| `JWTMiddlewareTests`    | Извлечение пользователя из токена, просроченный/невалидный токен         |
| `ProfileTests`          | Просмотр и обновление профиля                                            |
| `SoftDeleteTests`       | Деактивация аккаунта, запрет повторного входа                            |
| `ProductRBACTests`      | Права Admin vs User на Products (200 / 403 / 401)                        |
| `OrderRBACTests`        | Права Manager vs User на Orders                                          |
| `RBACEdgeCaseTests`     | Роль без правил, формат ошибок, защита от утечки данных                  |