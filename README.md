# ShoppingAPI — Backend для автоматизации закупок

Backend-приложение для сервиса заказа товаров из магазинов в розничной сети.
Реализовано на **Django REST Framework** с использованием **PostgreSQL**.
Взаимодействие с приложением через REST API.

Дипломный проект профессии «Python-разработчик: расширенный курс».

---

## Описание возможностей

- Регистрация с подтверждением email
- Авторизация по токену (вход по EMAIL)
- Каталог товаров с фильтрами
- Поиск по названию товара и категории
- Добавление, изменение количества, удаление
- Корзина с проверкой доступного количества
- Управление контактами
- Оформление заказа с выбором адреса
- Просмотр списка своих заказов и их деталей
- Email-уведомления о подтверждении и смене статуса
- **API поставщика** — импорт прайса, управление магазином, заказы
- Импорт из YAML-файла (API)
- Смена статуса заказа с уведомлением клиента
- Управление через Django-админку

---

## Технологии

| Компонент | Технология |
|-----------|-----------|
| Язык | Python |
| Фреймворк | Django |
| REST API | Django REST Framework |
| Аутентификация | Djoser + TokenAuthentication |
| БД | PostgreSQL |
| Драйвер БД | psycopg |
| Фильтрация | django-filter |
| Импорт данных | PyYAML |

---

## Установка и запуск

### 1. Клонирование

```bash
git clone https://github.com/VladimirMakarov88/ShoppingAPI.git
cd ShoppingAPI
```

### 2. Виртуальное окружение

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### 3. Зависимости

```bash
pip install -r requirements.txt
```

### 4. PostgreSQL

Создать БД:

```sql
CREATE DATABASE diplom
    WITH ENCODING 'UTF8'
         LC_COLLATE='C'
         LC_CTYPE='C'
         TEMPLATE=template0;

CREATE USER diplom_user WITH PASSWORD 'diplom_pass';
GRANT ALL PRIVILEGES ON DATABASE diplom TO diplom_user;

\c diplom
GRANT ALL ON SCHEMA public TO diplom_user;
```

### 5. Переменные окружения

```bash
cp .env.example .env
```

Заполяем `.env`:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=diplom
DB_USER=diplom_user
DB_PASSWORD=diplom_pass
DB_HOST=127.0.0.1
DB_PORT=5432

ADMIN_EMAIL=admin@example.com
DOMAIN=127.0.0.1:8000
DEFAULT_FROM_EMAIL=noreply@shoppingapi.local
```

`SECRET_KEY` сгенерировать:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Миграции и суперюзер

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 7. Импорт товаров из YAML

```bash
python manage.py import_yaml data/shop1.yaml
```

### 8. Запуск

```bash
python manage.py runserver
```

- **API:** http://127.0.0.1:8000/api/v1/
- **Админка:** http://127.0.0.1:8000/admin/

## Аутентификация

Регистрация и вход — **по email**.

### Регистрация

`POST /api/v1/auth/users/`

```json
{
  "username": "user1",
  "email": "user1@example.com",
  "password": "Secret12345",
  "re_password": "Secret12345",
  "type": "buyer"
}
```

`type`:
- `buyer` — покупатель,
- `shop` — поставщик.

### Активация

Ссылка приходит на email. В dev-режиме — **печатается в консоль `runserver`**.

Или активируйте через shell:

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; U = get_user_model(); u = U.objects.get(username='user1'); u.is_active = True; u.save()"
```

### Вход

`POST /api/v1/auth/token/login/`

```json
{"email": "user1@example.com", "password": "Secret12345"}
```

Ответ:

```json
{"auth_token": "abc123..."}
```

### Восстановление пароля

1. `POST /api/v1/auth/users/reset_password/` с `{"email": "user1@example.com"}`,
2. письмо со ссылкой (в консоли `runserver`),
3. `POST /api/v1/auth/users/reset_password_confirm/` с `{"uid": "...", "token": "...", "new_password": "..."}`.



---

## API Эндпоинты

Базовый URL: `http://127.0.0.1:8000/api/v1/`

### Аутентификация

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/auth/users/` | Регистрация |
| POST | `/auth/users/activation/` | Активация |
| POST | `/auth/token/login/` | Получение токена |
| POST | `/auth/token/logout/` | Выход |
| GET | `/auth/users/me/` | Текущий пользователь |
| POST | `/auth/users/reset_password/` | Восстановление пароля |


### Каталог

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/products/` | Список товаров |
| GET | `/products/{id}/` | Детали товара |
| GET | `/categories/` | Список категорий |
| GET | `/shops/` | Список магазинов |


**Параметры фильтрации `/products/`:**

| Параметр | Пример | Описание |
|----------|--------|----------|
| `category` | `?category=224` | ID категории |
| `shop_id` | `?shop_id=1` | ID магазина |
| `price_min` | `?price_min=50000` | Цена от |
| `price_max` | `?price_max=70000` | Цена до |
| `in_stock` | `?in_stock=true` | Только в наличии |
| `search` | `?search=iphone` | Поиск по названию и категории |


### Корзина и заказы

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/basket/` | Содержимое корзины |
| POST | `/basket/` | Добавить товар |
| DELETE | `/basket/remove_item/?item_id=1` | Удалить позицию |
| POST | `/orders/{id}/confirm/` | Подтвердить заказ |
| GET | `/orders/` | Список заказов |
| GET | `/orders/{id}/` | Детали заказа |
| POST | `/orders/{id}/set_status/` | Смена статуса (только админ) |


### Контакты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/contacts/` | Мои контакты |
| POST | `/contacts/` | Добавить контакт |
| PATCH | `/contacts/{id}/` | Изменить |
| DELETE | `/contacts/{id}/` | Удалить |


### API поставщика (`type='shop'`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/partner/shop/` | Мой магазин |
| PATCH | `/partner/shop/toggle_state/` | Вкл/выкл приём заказов |
| POST | `/partner/update/` | Импорт прайса — `{"file_path": "data/shop1.yaml"}` |
| GET | `/partner/orders/` | Заказы с моими товарами |

> Все запросы, кроме каталога и аутентификации, требуют заголовок:
> ```
> Authorization: Token <ваш_токен>
> ```

## Модели данных

| Модель | Назначение |
|--------|-----------|
| `User` | Пользователь: покупатель или поставщик (`type`) |
| `Shop` | Магазин (поставщик) |
| `Category` | Категория товаров (M2M к магазинам) |
| `Product` | Общая карточка товара |
| `ProductInfo` | Предложение в магазине: цена, остаток, характеристики |
| `Contact` | Контакт пользователя |
| `Order` | Заказ со статусами |
| `OrderItem` | Позиция заказа |


## Примеры запросов (curl)

### Регистрация

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/users/ \
  -H "Content-Type: application/json" \
  -d '{"username": "buyer1", "email": "buyer1@example.com", "password": "Secret12345", "re_password": "Secret12345", "type": "buyer"}'
```

### Логин

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "buyer1@example.com", "password": "Secret12345"}'
```

### Каталог с фильтрами

```bash
curl "http://127.0.0.1:8000/api/v1/products/?category=224&price_max=70000"
curl "http://127.0.0.1:8000/api/v1/products/?search=iphone"
```

### Корзина

```bash
curl -X POST http://127.0.0.1:8000/api/v1/basket/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <токен>" \
  -d '{"product_info_id": 1, "quantity": 1}'
```

### Адрес

```bash
curl -X POST http://127.0.0.1:8000/api/v1/contacts/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <токен>" \
  -d '{"type": "address", "city": "Москва", "street": "Тверская", "house": "1"}'
```


### Подтверждение заказа

```bash
curl -X POST http://127.0.0.1:8000/api/v1/orders/1/confirm/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <токен>" \
  -d '{"contact_id": 1}'
```

### Импорт прайса поставщиком

```bash
curl -X POST http://127.0.0.1:8000/api/v1/partner/update/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <токен_поставщика>" \
  -d '{"file_path": "data/shop1.yaml"}'
```



## Docker

### 1. Переменные окружения

```bash
cp .env.docker.example .env.docker
```

Отредактируйте `.env.docker` (при необходимости — `SECRET_KEY`).

### 2. Сборка и запуск

```bash
docker compose up --build
```

- **API:** http://127.0.0.1:8000/api/v1/
- **Админка:** http://127.0.0.1:8000/admin/

### 3. Суперпользователь и импорт

```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py import_yaml data/shop1.yaml
```

### 4. Остановка

```bash
docker compose down
docker compose down -v
```

## Email

По умолчанию письма **печатаются в консоль** (`console.EmailBackend`).

Для реальной отправки необходимо настроить SMTP в `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your@yandex.ru
EMAIL_HOST_PASSWORD=app-password
```

**Письма отправляются при:**
- регистрации (активация),
- подтверждении заказа (клиенту + админу),
- смене статуса заказа (клиенту).

---


- **Celery** — не используется, письма отправляются синхронно
- **Поставщик** — только импорт прайса и смена `state`; ручное редактирование цен через API не реализовано

---