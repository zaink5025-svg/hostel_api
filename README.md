# Hostel Management API (Flask + MySQL)

Your console program (`main.py`, text files) converted into a REST API that stores data in MySQL and can be tested with Postman.

```
Postman  --HTTP/JSON-->  Flask API (app.py)  --SQL-->  MySQL (hostel_db)
```

## Project files

| File | Purpose |
|---|---|
| `schema.sql` | Creates the database and 8 tables (replaces your 8 `.txt` files) |
| `db.py` | MySQL connection pool and helper functions (replaces `read_all`, `write_all`, `find_line` ...) |
| `app.py` | All API endpoints (replaces the menu and every `input()`/`print()` function) |
| `.env.example` | Template for your database password/settings |
| `requirements.txt` | Python packages needed |
| `Hostel_API.postman_collection.json` | Ready-made Postman requests (29 requests) |

## Setup (7 steps)

**1. Install** Python 3.9+, MySQL Server (MySQL Installer or XAMPP/MariaDB both work) and Postman.

**2. Create a virtual environment and install packages**

```bash
cd hostel_api
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

**3. Create the database and tables**

```bash
mysql -u root -p < schema.sql
```

(Or open `schema.sql` in MySQL Workbench and run it.)

**4. Create your `.env` file**: copy `.env.example` to `.env` and set `DB_PASSWORD` to your MySQL root password.

**5. Start the API**

```bash
python app.py
```

Open http://127.0.0.1:5000/ in a browser. You should see `"API is running"`.

**6. Import the collection into Postman**: *Import* -> choose `Hostel_API.postman_collection.json`.

**7. Run it**: open the collection, click **Run** (Collection Runner), and run folders 1 to 9 in order. Each create request saves its ID into a variable, so the later requests work automatically.

## Endpoints

| Menu # | Action | Method | URL | Body |
|---|---|---|---|---|
| 1 | Add student | POST | `/students` | first_name, last_name, dob, contact, gender (+ optional father_name, mother_name, email, address, vehicle_number, college_workplace) |
| 2 | List students | GET | `/students` | |
| 3 | View student | GET | `/students/<id>` | |
| 4 | Update student | PUT | `/students/<id>` | same as add |
| 5 | Delete student | DELETE | `/students/<id>` | |
| 6 | Add room (+beds) | POST | `/rooms` | room_number, floor, capacity, gender |
| 7 | List rooms | GET | `/rooms` | |
| 8 | View room beds | GET | `/rooms/<id>/beds` | |
| 9 | Available beds | GET | `/beds/available` | |
| 10 | Allocate student | POST | `/allocations` | student_id, room_id, bed_id |
| 11 | List allocations | GET | `/allocations` (`?status=Active`) | |
| 12 | Checkout allocation | PATCH | `/allocations/<id>/checkout` | |
| 13 | Add service | POST | `/services` | name, description |
| 14 | List services | GET | `/services` | |
| 15 | Add visitor | POST | `/visitors` | student_id, visitor_name, contact, reason, address |
| 16 | List visitors | GET | `/visitors` | |
| 17 | Visitor checkout | PATCH | `/visitors/<id>/checkout` | |
| 18 | Apply leave | POST | `/leaves` | student_id, reason, application_date, return_date |
| 19 | List leaves | GET | `/leaves` (`?status=Pending`) | |
| 20 | Approve leave | PATCH | `/leaves/<id>/approve` | |
| 21 | Reject leave | PATCH | `/leaves/<id>/reject` | |
| 22 | Student OUT | POST | `/attendance/out` | student_id, purpose, remarks |
| 23 | Student IN | POST | `/attendance/in` | student_id |
| 24 | List attendance | GET | `/attendance` (`?student_id=1`) | |
| 25 | Dashboard | GET | `/dashboard` | |

Dates use `YYYY-MM-DD`. Gender must be `Male`, `Female` or `Other`.

## Response format

Success:
```json
{ "success": true, "message": "Student added", "data": { "id": 1 } }
```
Error:
```json
{ "success": false, "error": "Student not found" }
```

| Status | Meaning |
|---|---|
| 200 / 201 | OK / Created |
| 400 | Bad input (missing field, wrong date format ...) |
| 404 | Record or URL not found |
| 405 | Wrong HTTP method for that URL |
| 409 | Conflict (bed already taken, student already allocated, cannot delete ...) |
| 500 | Server or database problem |

## Troubleshooting

| Problem | Fix |
|---|---|
| `Access denied for user 'root'` | Wrong `DB_PASSWORD` in `.env` |
| `Unknown database 'hostel_db'` | Step 3 was not run |
| `Can't connect to MySQL server` | MySQL service is not running (start it from Services / XAMPP) |
| `ModuleNotFoundError` | Virtual environment not activated, or `pip install -r requirements.txt` not run |
| Postman "Could not send request" | `python app.py` is not running, or `base_url` variable is wrong |
| 400 "Request body must be valid JSON" | In Postman use Body -> raw -> JSON, and a valid JSON body |
| 405 Method Not Allowed | Wrong method (e.g. GET instead of POST) |
| `Authentication plugin 'caching_sha2_password'` error | Update the package: `pip install -U mysql-connector-python` |

## Ideas to improve later

- Login with JWT tokens so only wardens/admins can call the API
- Check that a student's gender matches the room gender when allocating
- Pagination (`?page=1&limit=20`) on list endpoints
- Swagger/OpenAPI documentation (e.g. `flasgger`)
- Deploy with `gunicorn` (Linux) or `waitress` (Windows) instead of `app.run(debug=True)`