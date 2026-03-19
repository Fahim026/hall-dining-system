# 🍽️ Meal Management System — Django Backend

A complete REST API backend for managing hostel/mess meal operations with JWT authentication.

---

## 🚀 Setup Instructions

### 1. Clone & Navigate
```bash
cd meal_management
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your MySQL credentials and secret key
```

### 5. Create MySQL Database
```sql
CREATE DATABASE meal_management_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 6. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create Admin User
```bash
python manage.py createsuperuser
```

### 8. Run Development Server
```bash
python manage.py runserver
```

API is now live at: `http://localhost:8000/api/`

---

## 📡 API Reference

All endpoints are prefixed with `/api/`
Authentication: `Authorization: Bearer <access_token>`

---

### 🔐 Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register/` | No | Register new student |
| POST | `/auth/login/` | No | Login, get JWT tokens |
| POST | `/auth/logout/` | Yes | Logout (blacklist token) |
| POST | `/auth/token/refresh/` | No | Refresh access token |
| GET/PUT | `/auth/me/` | Yes | View/update own profile |
| POST | `/auth/change-password/` | Yes | Change password |

**Login Request:**
```json
{ "email": "student@example.com", "password": "password123" }
```
**Login Response:**
```json
{
  "user": { "id": 1, "name": "John", "role": "student", ... },
  "access": "<jwt_token>",
  "refresh": "<refresh_token>"
}
```

---

### 👨‍💼 Admin: User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/admin/users/` | List all students / Create student |
| GET/PUT/DELETE | `/admin/users/<id>/` | Manage individual student |
| POST | `/admin/users/<id>/toggle-active/` | Enable/disable student account |

---

### 💰 Deposits

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/deposits/` | All | List deposits (own for student, all for admin) |
| POST | `/deposits/` | Student | Submit monthly deposit |
| GET/PUT | `/deposits/<id>/` | All | View/edit deposit |
| POST | `/deposits/<id>/confirm/` | Admin | Confirm deposit received |

**Student submits deposit:**
```json
{ "deposited_amount": 3000, "notes": "Cash payment" }
```

---

### 🍽️ Daily Meal Entry

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/meal-entries/` | All | List entries (filtered by query params) |
| POST | `/meal-entries/` | Admin | Add single meal entry |
| GET/PUT/DELETE | `/meal-entries/<id>/` | Admin | Manage entry |
| POST | `/meal-entries/bulk/` | Admin | Bulk entry for all students |

**Bulk Entry (Admin):**
```json
{
  "date": "2024-12-15",
  "entries": [
    { "student_id": 1, "breakfast": true, "lunch": true, "dinner": false },
    { "student_id": 2, "breakfast": false, "lunch": true, "dinner": true }
  ]
}
```

**Query params:** `?date=2024-12-15` | `?month=12&year=2024` | `?student_id=1`

---

### 🚫 Meal Off Requests

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/meal-off/` | All | List requests |
| POST | `/meal-off/` | Student | Submit meal-off request |
| GET/DELETE | `/meal-off/<id>/` | All | View / Cancel (student) |
| POST | `/meal-off/<id>/review/` | Admin | Approve or reject |
| GET/POST | `/meal-off/limit/` | All/Admin | Get or set monthly limit |

**Student Request:**
```json
{
  "start_date": "2024-12-20",
  "end_date": "2024-12-22",
  "skip_breakfast": false,
  "skip_lunch": true,
  "skip_dinner": true,
  "reason": "Going home for vacation"
}
```

**Admin Review:**
```json
{ "status": "approved", "admin_note": "Approved. Bon voyage!" }
```

**Set Limit (Admin):**
```json
{ "max_days_per_month": 7 }
```

---

### 👥 Guest Meal Requests

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/guest-meals/` | All | List requests |
| POST | `/guest-meals/` | Student | Request guest meal |
| GET/DELETE | `/guest-meals/<id>/` | All | View / Cancel |
| POST | `/guest-meals/<id>/review/` | Admin | Approve/reject + set extra charge |

**Student Request:**
```json
{
  "guest_name": "Uncle Karim",
  "guest_count": 2,
  "date": "2024-12-25",
  "meal_type": "lunch",
  "reason": "Family visit"
}
```

**Admin Review:**
```json
{ "status": "approved", "extra_charge": 150, "admin_note": "Welcome!" }
```

---

### 🛒 Bazar Entries

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/bazar/` | All | List entries |
| POST | `/bazar/` | Admin | Add bazar item |
| GET/PUT/DELETE | `/bazar/<id>/` | Admin | Manage entry |
| GET | `/bazar/summary/<month>/<year>/` | All | Monthly cost summary |

**Add Bazar Item:**
```json
{
  "date": "2024-12-15",
  "item_name": "Rice",
  "quantity": "20 kg",
  "unit_price": 65.00,
  "total_cost": 1300.00,
  "notes": "Fine quality"
}
```

---

### 📊 Meal Rate

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/meal-rates/` | All | List all rates |
| POST | `/meal-rates/` | Admin | Create rate manually |
| GET/PUT | `/meal-rates/<id>/` | Admin | Manage rate |
| POST | `/meal-rates/finalize/<month>/<year>/` | Admin | Auto-calculate from bazar cost |

Auto-calculate example: `POST /api/meal-rates/finalize/12/2024/`
This divides total bazar cost by total meals eaten to get rate per meal.

---

### 🔔 Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/notifications/` | List all notifications |
| POST | `/notifications/read-all/` | Mark all as read |
| POST | `/notifications/<id>/read/` | Mark one as read |
| DELETE | `/notifications/<id>/` | Delete notification |

---

### 📈 Dashboards

**Student Dashboard:** `GET /dashboard/student/?month=12&year=2024`
```json
{
  "month": 12, "year": 2024,
  "deposited_amount": 3000.00,
  "deposit_confirmed": true,
  "total_meals_eaten": 45,
  "meal_rate": 55.50,
  "total_cost": 2497.50,
  "guest_charges": 150.00,
  "balance_remaining": 352.50,
  "meal_off_days_used": 3,
  "meal_off_days_limit": 5,
  "meal_off_days_remaining": 2,
  "pending_requests": { "meal_off": 1, "guest_meal": 0 },
  "unread_notifications": 2
}
```

**Admin Dashboard:** `GET /dashboard/admin/?month=12&year=2024`
```json
{
  "total_students": 25,
  "total_confirmed_deposits": 75000.00,
  "total_bazar_cost": 62000.00,
  "total_meals_this_month": 1800,
  "current_meal_rate": 55.50,
  "balance": 13000.00,
  "pending_meal_offs": 3,
  "pending_guest_meals": 1,
  "pending_deposits": 2
}
```

---

## 🗂️ Project Structure

```
meal_management/
├── manage.py
├── requirements.txt
├── .env.example
├── meal_management/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── api/
    ├── models.py       ← All database models
    ├── serializers.py  ← Request/response validation
    ├── views.py        ← Business logic & API endpoints
    ├── urls.py         ← URL routing
    ├── permissions.py  ← IsAdmin, IsStudent, IsAdminOrReadOwn
    └── admin.py        ← Django admin panel
```

## 🔑 User Roles

- **Admin**: Can manage all students, confirm deposits, enter daily meals, review all requests, enter bazar costs, finalize meal rates
- **Student**: Can submit deposit, view own stats, request meal off (with monthly limit), request guest meal, view notifications

## 💡 Key Business Rules

1. Students submit their deposit at the start of each month → Admin confirms
2. Admin enters daily meal counts (breakfast/lunch/dinner) for each student
3. Admin enters daily bazar/market costs
4. Admin finalizes monthly meal rate = Total Bazar Cost ÷ Total Meals
5. Students see their balance = Deposit - (Meals × Rate) - Guest Charges
6. Students can request meal-off days (up to admin-configured monthly limit)
7. Students can request guest meals → Admin approves and sets extra charge
8. All approvals/rejections trigger automatic notifications to students
