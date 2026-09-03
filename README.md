# Django n8n Telegram Notifications

A Django web application that collects contact form submissions, persists them to PostgreSQL, and forwards each submission to a Telegram chat via an n8n webhook.

---

## Architecture

```
Browser
   │
   │  GET/POST /submit/
   ▼
Django (submissions app)
   │                  │
   │  Saves data      │  transaction.on_commit()
   ▼                  ▼
PostgreSQL          n8n Webhook
                       │
                       │  Telegram node
                       ▼
                    Telegram Chat
```

---

## Prerequisites

- Python 3.11+
- PostgreSQL (running and accessible)
- pip

---

## Local Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd world-h
```

### 2. Create and activate a virtual environment

**Linux / macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bat
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Copy the environment file

```bash
cp .env.example .env
```

### 5. Edit `.env`

Open `.env` and fill in the required values:

```
SECRET_KEY=<long-random-string>
DATABASE_URL=postgres://user:password@localhost:5432/yourdbname
N8N_WEBHOOK_URL=https://your-n8n-instance.example.com/webhook/your-webhook-id
N8N_WEBHOOK_SECRET=your-webhook-secret-here
```

See the [Environment Variables](#environment-variables) section for a full description of each variable.

### 6. Create the PostgreSQL database

```bash
createdb yourdbname
```

Or use `psql`:

```sql
CREATE DATABASE yourdbname;
```

### 7. Run migrations

```bash
python manage.py migrate
```

### 8. Create a superuser

```bash
python manage.py createsuperuser
```

### 9. Start the development server

```bash
python manage.py runserver
```

### 10. Open the form

Navigate to [http://localhost:8000/submit/](http://localhost:8000/submit/) in your browser.

---

## Environment Variables

| Variable             | Required | Description                                                                                      |
|----------------------|----------|--------------------------------------------------------------------------------------------------|
| `SECRET_KEY`         | Yes      | Django secret key. Use a long, random string in production. Never commit this value.             |
| `DEBUG`              | No       | Set to `True` during local development only. Defaults to `False`.                               |
| `ALLOWED_HOSTS`      | No       | Comma-separated list of allowed hostnames (e.g. `example.com,www.example.com`).                 |
| `DATABASE_URL`       | Yes      | PostgreSQL connection string. Format: `postgres://USER:PASSWORD@HOST:PORT/DBNAME`.               |
| `N8N_WEBHOOK_URL`    | Yes      | Full URL of the n8n Webhook node that receives submission data.                                  |
| `N8N_WEBHOOK_SECRET` | No       | Shared secret sent as the `X-Webhook-Secret` header. Set the same value in n8n to verify origin.|

---

## n8n Configuration

### 1. Create a new workflow

Log in to your n8n instance and click **New Workflow**.

### 2. Add a Webhook node

- Add a **Webhook** node as the trigger
- Set **HTTP Method** to `POST`
- Set **Path** to something like `/new-submission`
- Set **Authentication** to `None` (you will validate the secret manually in the next step)
- Copy the **Webhook URL** shown in the node

### 3. Set the webhook URL in `.env`

Paste the copied URL as the value for `N8N_WEBHOOK_URL` in your `.env` file.

### 4. Add a "Validate Secret" IF node

- Add an **IF** node after the Webhook node
- Add a condition: `{{ $json.headers['x-webhook-secret'] }}` equals `your-webhook-secret-here`
- Route the **True** branch to your Telegram node; the **False** branch can be left empty or connected to a Stop node

### 5. Add a Telegram node

- Add a **Telegram** node on the True branch
- Connect your Telegram credentials (Bot Token + Chat ID)
- Compose the message using the payload fields (see below)

### 6. Activate the workflow

Toggle the workflow to **Active** in the top-right corner of the n8n editor.

### JSON payload reference

Every submission sends the following JSON body to the webhook:

```json
{
  "id": 42,
  "name": "Alice",
  "phone": "+1-555-0100",
  "email": "alice@example.com",
  "message": "Hello there",
  "created_at": "2024-01-15T10:30:00+00:00"
}
```

| Field        | Type    | Notes                                           |
|--------------|---------|-------------------------------------------------|
| `id`         | integer | Database primary key of the submission          |
| `name`       | string  | Submitter's full name                           |
| `phone`      | string  | Submitter's phone number                        |
| `email`      | string  | Submitter's email address (empty string if not provided) |
| `message`    | string  | The message body                                |
| `created_at` | string  | ISO 8601 UTC timestamp of when the form was submitted |

---

## Running Tests

```bash
python manage.py test submissions --settings=config.test_settings --verbosity=2
```

---

## Admin

Access the Django admin at [http://localhost:8000/admin/](http://localhost:8000/admin/) using the superuser credentials you created earlier.

The admin panel lets you view all submissions along with their n8n notification status (`n8n_notified`, `n8n_notified_at`, `n8n_notification_error`).

---

## Project Structure

```
project-root/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── submissions/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── services.py
│   ├── urls.py
│   ├── views.py
│   └── templates/
│       └── submissions/
│           ├── base.html
│           ├── submit.html
│           └── success.html
├── .env.example
├── .gitignore
├── manage.py
├── README.md
└── requirements.txt
```
