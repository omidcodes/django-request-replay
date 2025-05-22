
# 🛠️ Django Request Replay

## 📌 Project Overview

In a recent project, our team encountered a significant challenge with a **stateful system** that would revert to factory settings after reboots or power losses. Additionally, there was a need for a mechanism to **accurately reproduce system states** for debugging purposes when customers encountered internal server errors. Traditional methods like system logs and error-tracking tools such as Sentry were insufficient for replicating exact requests in a raw debugging environment.

### My Approach to Fix it

To tackle this issue, I developed a middleware solution within our Django Backend Core. This middleware was designed to record and save essential API requests to the database. This approach enabled us to restore the system to its last known state by replaying these saved requests. The middleware was engineered to capture request details upon their arrival, selectively save them based on predefined criteria, and utilize this data for effective system restoration.

This solution not only resolved the immediate issue of system state preservation but also enhanced our debugging capabilities, allowing for a more reliable and maintainable system.

### Code Workflow Summary

- **Capture API Request Details**: When an API request is received by the Django web service, the middleware immediately captures its details.
- **Evaluate Saving Criteria**: The middleware then evaluates whether the request meets the criteria to be saved (based on its method and the response status).
- **Database Saving**: If the request is savable, the middleware creates an instance of `DjangoRequestsHistoryModel` and commits the request details to the database.

---

## ✅ Architecture Overview

### 1. `request_logger` App
- Contains the custom middleware to track API requests.
- Uses `DjangoRequestsHistoryModel` to store request/response data persistently.
- Controlled via flexible Django settings for request filtering and customization.

### 2. `command_queue_simulation` App
- Simulates a volatile stateful system with an in-memory command queue (`SIMULATED_STATE`).
- Exposes endpoints that accept and store commands temporarily (cleared on reboot).

---

## ⚙️ Configuration

The logging behavior can be controlled in `settings.py` using the following keys:

```python
DJANGO_REQUESTS_HISTORY_ENABLE = True
DJANGO_REQUESTS_HISTORY_SAVABLE_REQUEST_METHODS = ('POST', 'PATCH', 'PUT', 'DELETE')
DJANGO_REQUESTS_HISTORY_EXCLUDING_URL_NAMES = ()
DJANGO_REQUESTS_HISTORY_VIEW_FILTER = {}
DJANGO_REQUESTS_HISTORY_VIEW_ORDER_BY = "created"
DJANGO_REQUESTS_HISTORY_VISIBLE_COLUMNS = "__all__"
```

---

## 🧪 Example Use Case

```http
POST /api/commands
{
  "command": "restart wifi"
}
```

This command will:
- Be saved in memory (`SIMULATED_STATE`)
- Be logged persistently by the middleware if eligible

---

## 🚀 Features

- Smart request filtering based on settings
- Records request/response metadata (method, path, user, IP, status)
- Pluggable middleware for use in any Django project
- Compatible with Django Admin or custom dashboards

---

## 🏁 Getting Started

```bash
git clone git@github.com:omidcodes/django-request-replay.git
cd django-request-replay
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```

---

## 📂 Project Structure

```
├── request_logger/
│   ├── middlewares.py       # Request logging middleware
│   ├── models.py            # DjangoRequestsHistoryModel
│   ├── conf.py              # Configuration parser
│   └── ...
├── command_queue_simulation/
│   ├── views.py             # Simulated in-memory queue logic
│   └── ...
```

---

## 🔄 Future Improvements

- API or management command to replay stored requests
- Admin view with dynamic filters and labels

---

## © License

MIT License