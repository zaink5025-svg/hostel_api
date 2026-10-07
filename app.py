"""
app.py - Hostel Management REST API (Flask + MySQL)

Your old main.py had a menu (1..25) and used input()/print().
Now every menu option is an API "endpoint" (a URL).
Postman (or any app) sends a request to the URL, and we send JSON back.

    Menu option                 ->  Endpoint
    1  Add Student              ->  POST   /students
    2  List Students            ->  GET    /students
    3  View Student             ->  GET    /students/<id>
    4  Update Student           ->  PUT    /students/<id>
    5  Delete Student           ->  DELETE /students/<id>
    ... and so on (full table is in README.md)
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import mysql.connector
from flask import Flask, jsonify, request
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException

from db import db_cursor, execute, query_all, query_one

# APP SETUP

class CustomJSONProvider(DefaultJSONProvider):
    """Teach Flask how to turn MySQL types (dates, decimals) into JSON."""

    sort_keys = False  # keep keys in the order we wrote them

    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat(sep=" ") if isinstance(o, datetime) else o.isoformat()
        if isinstance(o, timedelta):
            return str(o)
        if isinstance(o, Decimal):
            return int(o) if o == o.to_integral_value() else float(o)
        return super().default(o)


app = Flask(__name__)
app.json = CustomJSONProvider(app)

GENDERS = ("Male", "Female", "Other")

# RESPONSE + ERROR HELPERS

class ApiError(Exception):
    """Raise this anywhere to stop and return a clean JSON error."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def ok(data=None, message=None, status=200):
    """Every successful response has the same shape."""
    return jsonify({"success": True, "message": message, "data": data}), status


@app.errorhandler(ApiError)
def handle_api_error(error):
    return jsonify({"success": False, "error": error.message}), error.status


@app.errorhandler(HTTPException)
def handle_http_error(error):
    # 404 (wrong URL), 405 (wrong method, e.g. GET instead of POST) ...
    return jsonify({"success": False, "error": error.description}), error.code


@app.errorhandler(mysql.connector.IntegrityError)
def handle_integrity_error(error):
    if error.errno == 1062:
        return jsonify({"success": False,
                        "error": "Duplicate value: this record already exists."}), 409
    if error.errno == 1451:
        return jsonify({"success": False,
                        "error": "Cannot delete: other records (allocations, leaves, "
                                 "visitors, attendance ...) still depend on it."}), 409
    if error.errno == 1452:
        return jsonify({"success": False,
                        "error": "Related record does not exist."}), 400
    return jsonify({"success": False, "error": "Database integrity error."}), 409


@app.errorhandler(mysql.connector.Error)
def handle_database_error(error):
    app.logger.exception("Database error")
    # NOTE: 'detail' is handy while learning. Remove it in production.
    return jsonify({"success": False, "error": "Database error",
                    "detail": str(error)}), 500


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    app.logger.exception("Unexpected error")
    return jsonify({"success": False, "error": "Internal server error"}), 500

# VALIDATION HELPERS

def get_json():
    """Read the JSON body that Postman sends."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise ApiError("Request body must be valid JSON "
                       "(Body -> raw -> JSON in Postman).")
    return data


def require(data, fields):
    """Make sure the required fields are present and not empty."""
    missing = [f for f in fields if data.get(f) in (None, "")]

    if missing:
        raise ApiError("Missing required field(s): " + ", ".join(missing))


def to_int(value, field):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ApiError(field + " must be a whole number")

    if number <= 0:
        raise ApiError(field + " must be greater than 0")

    return number


def to_date(value, field):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise ApiError(field + " must be in YYYY-MM-DD format")


def check_gender(value):
    if value not in GENDERS:
        raise ApiError("gender must be one of: " + ", ".join(GENDERS))
    return value


def ensure_exists(table, record_id, label, cur=None):
    """Return 404 if the row does not exist. (table names come from our code only)"""
    sql = "SELECT id FROM " + table + " WHERE id = %s"

    if cur is None:
        row = query_one(sql, (record_id,))
    else:
        cur.execute(sql, (record_id,))
        row = cur.fetchone()

    if row is None:
        raise ApiError(label + " not found", 404)

# HOME

@app.get("/")
def home():
    return ok({"service": "Hostel Management API", "version": "1.0"},
              "API is running")

# STUDENTS

STUDENT_REQUIRED = ["first_name", "last_name", "dob", "contact", "gender"]


def student_values(data):
    """Validate the body and return values in the same order as the SQL below."""
    require(data, STUDENT_REQUIRED)
    check_gender(data["gender"])
    to_date(data["dob"], "dob")

    return (
        data["first_name"],
        data["last_name"],
        data.get("father_name"),
        data.get("mother_name"),
        data["dob"],
        data["contact"],
        data.get("email"),
        data.get("address"),
        data.get("vehicle_number"),
        data.get("college_workplace"),
        data["gender"],
    )


@app.post("/students")
def add_student():
    values = student_values(get_json())

    student_id = execute(
        """INSERT INTO students
           (first_name, last_name, father_name, mother_name, dob, contact,
            email, address, vehicle_number, college_workplace, gender)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        values,
    )

    return ok({"id": student_id}, "Student added", 201)


@app.get("/students")
def list_students():
    rows = query_all(
        """SELECT id, first_name, last_name, gender, contact
           FROM students ORDER BY id"""
    )
    return ok(rows)

@app.get("/students/<int:student_id>")
def view_student(student_id):
    row = query_one("SELECT * FROM students WHERE id = %s", (student_id,))

    if row is None:
        raise ApiError("Student not found", 404)

    return ok(row)

@app.put("/students/<int:student_id>")
def update_student(student_id):
    values = student_values(get_json())
    ensure_exists("students", student_id, "Student")

    execute(
        """UPDATE students SET
             first_name = %s, last_name = %s, father_name = %s, mother_name = %s,
             dob = %s, contact = %s, email = %s, address = %s,
             vehicle_number = %s, college_workplace = %s, gender = %s
           WHERE id = %s""",
        values + (student_id,),
    )

    return ok({"id": student_id}, "Student updated")


@app.delete("/students/<int:student_id>")
def delete_student(student_id):
    ensure_exists("students", student_id, "Student")

    # If the student has allocations/leaves/etc., MySQL refuses and our
    # IntegrityError handler above returns a friendly 409 message.
    execute("DELETE FROM students WHERE id = %s", (student_id,))

    return ok(None, "Student deleted")

# ROOMS AND BEDS

@app.post("/rooms")
def add_room():
    data = get_json()
    require(data, ["room_number", "floor", "capacity", "gender"])

    floor = data["floor"]
    capacity = to_int(data["capacity"], "capacity")
    check_gender(data["gender"])

    if capacity > 20:
        raise ApiError("capacity cannot be more than 20")

    # Room + all its beds are created together (all or nothing).
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO rooms (room_number, floor, capacity, gender) "
            "VALUES (%s, %s, %s, %s)",
            (data["room_number"], floor, capacity, data["gender"]),
        )
        room_id = cur.lastrowid

        beds = [(room_id, "Bed" + str(i)) for i in range(1, capacity + 1)]
        cur.executemany("INSERT INTO beds (room_id, bed_name) VALUES (%s, %s)", beds)

    return ok({"id": room_id, "beds_created": capacity}, "Room added", 201)


@app.get("/rooms")
def list_rooms():
    rows = query_all(
        """SELECT r.id, r.room_number, r.floor, r.capacity, r.gender,
                  COUNT(b.id) AS total_beds,
                  COALESCE(SUM(b.status = 'Available'), 0) AS available_beds,
                  CASE WHEN COALESCE(SUM(b.status = 'Available'), 0) > 0
                       THEN 'Available' ELSE 'Full' END AS status
           FROM rooms r
           LEFT JOIN beds b ON b.room_id = r.id
           GROUP BY r.id
           ORDER BY r.id"""
    )
    return ok(rows)


@app.get("/rooms/<int:room_id>/beds")
def view_room_beds(room_id):
    ensure_exists("rooms", room_id, "Room")

    rows = query_all(
        "SELECT id, room_id, bed_name, status FROM beds WHERE room_id = %s ORDER BY id",
        (room_id,),
    )
    return ok(rows)


@app.get("/beds/available")
def list_available_beds():
    rows = query_all(
        """SELECT b.id AS bed_id, b.room_id, r.room_number, b.bed_name
           FROM beds b
           JOIN rooms r ON r.id = b.room_id
           WHERE b.status = 'Available'
           ORDER BY b.id"""
    )
    return ok(rows)

# ALLOCATIONS

@app.post("/allocations")
def create_allocation():
    data = get_json()
    require(data, ["student_id", "room_id", "bed_id"])

    student_id = to_int(data["student_id"], "student_id")
    room_id = to_int(data["room_id"], "room_id")
    bed_id = to_int(data["bed_id"], "bed_id")

    with db_cursor() as cur:
        ensure_exists("students", student_id, "Student", cur)
        ensure_exists("rooms", room_id, "Room", cur)

        # FOR UPDATE locks the bed row so two requests cannot book the same bed.
        cur.execute("SELECT id, room_id, status FROM beds WHERE id = %s FOR UPDATE",
                    (bed_id,))
        bed = cur.fetchone()

        if bed is None:
            raise ApiError("Bed not found", 404)
        if bed["room_id"] != room_id:
            raise ApiError("Bed does not belong to this room")
        if bed["status"] != "Available":
            raise ApiError("Bed is not available", 409)

        cur.execute(
            "SELECT id FROM allocations WHERE student_id = %s AND status = 'Active'",
            (student_id,),
        )
        if cur.fetchone() is not None:
            raise ApiError("Student already has an active allocation", 409)

        cur.execute(
            """INSERT INTO allocations (student_id, room_id, bed_id, allocated_date)
               VALUES (%s, %s, %s, CURDATE())""",
            (student_id, room_id, bed_id),
        )
        allocation_id = cur.lastrowid

        cur.execute("UPDATE beds SET status = 'Occupied' WHERE id = %s", (bed_id,))

    return ok({"id": allocation_id}, "Allocation created", 201)


@app.get("/allocations")
def list_allocations():
    sql = """SELECT al.id, al.student_id,
                    CONCAT(s.first_name, ' ', s.last_name) AS student_name,
                    al.room_id, r.room_number, al.bed_id, b.bed_name,
                    al.allocated_date, al.checkout_date, al.status
             FROM allocations al
             JOIN students s ON s.id = al.student_id
             JOIN rooms r    ON r.id = al.room_id
             JOIN beds b     ON b.id = al.bed_id"""
    params = ()

    status = request.args.get("status")  # optional: /allocations?status=Active
    if status:
        sql += " WHERE al.status = %s"
        params = (status,)

    return ok(query_all(sql + " ORDER BY al.id", params))


@app.patch("/allocations/<int:allocation_id>/checkout")
def checkout_allocation(allocation_id):
    with db_cursor() as cur:
        cur.execute("SELECT id, bed_id, status FROM allocations WHERE id = %s FOR UPDATE",
                    (allocation_id,))
        allocation = cur.fetchone()

        if allocation is None:
            raise ApiError("Allocation not found", 404)
        if allocation["status"] == "Checked-out":
            raise ApiError("Already checked out", 409)

        cur.execute(
            "UPDATE allocations SET status = 'Checked-out', checkout_date = CURDATE() "
            "WHERE id = %s",
            (allocation_id,),
        )
        cur.execute("UPDATE beds SET status = 'Available' WHERE id = %s",
                    (allocation["bed_id"],))

    return ok(None, "Checked out. Bed is now available.")

# SERVICES

@app.post("/services")
def add_service():
    data = get_json()
    require(data, ["name"])

    service_id = execute(
        "INSERT INTO services (name, description) VALUES (%s, %s)",
        (data["name"], data.get("description")),
    )
    return ok({"id": service_id}, "Service added", 201)


@app.get("/services")
def list_services():
    return ok(query_all("SELECT id, name, description FROM services ORDER BY id"))

# VISITORS

@app.post("/visitors")
def add_visitor():
    data = get_json()
    require(data, ["student_id", "visitor_name", "contact", "reason"])

    student_id = to_int(data["student_id"], "student_id")
    ensure_exists("students", student_id, "Student")

    visitor_id = execute(
        """INSERT INTO visitors
           (student_id, visitor_name, contact, reason, address, check_in)
           VALUES (%s, %s, %s, %s, %s, NOW())""",
        (student_id, data["visitor_name"], data["contact"],
         data["reason"], data.get("address")),
    )
    return ok({"id": visitor_id}, "Visitor added", 201)


@app.get("/visitors")
def list_visitors():
    rows = query_all(
        """SELECT v.id, v.student_id,
                  CONCAT(s.first_name, ' ', s.last_name) AS student_name,
                  v.visitor_name, v.contact, v.reason,
                  v.check_in, v.check_out, v.status
           FROM visitors v
           JOIN students s ON s.id = v.student_id
           ORDER BY v.id"""
    )
    return ok(rows)


@app.patch("/visitors/<int:visitor_id>/checkout")
def checkout_visitor(visitor_id):
    visitor = query_one("SELECT id, status FROM visitors WHERE id = %s", (visitor_id,))

    if visitor is None:
        raise ApiError("Visitor not found", 404)
    if visitor["status"] == "CheckedOut":
        raise ApiError("Already checked out", 409)

    execute(
        "UPDATE visitors SET check_out = NOW(), status = 'CheckedOut' WHERE id = %s",
        (visitor_id,),
    )
    return ok(None, "Visitor checked out")

# LEAVES

@app.post("/leaves")
def apply_leave():
    data = get_json()
    require(data, ["student_id", "reason", "application_date", "return_date"])

    student_id = to_int(data["student_id"], "student_id")
    start = to_date(data["application_date"], "application_date")
    end = to_date(data["return_date"], "return_date")

    if end < start:
        raise ApiError("return_date cannot be before application_date")

    ensure_exists("students", student_id, "Student")

    leave_id = execute(
        """INSERT INTO leaves (student_id, reason, application_date, return_date)
           VALUES (%s, %s, %s, %s)""",
        (student_id, data["reason"], data["application_date"], data["return_date"]),
    )
    return ok({"id": leave_id}, "Leave applied (status: Pending)", 201)


@app.get("/leaves")
def list_leaves():
    sql = """SELECT l.id, l.student_id,
                    CONCAT(s.first_name, ' ', s.last_name) AS student_name,
                    l.reason, l.application_date, l.return_date, l.status
             FROM leaves l
             JOIN students s ON s.id = l.student_id"""
    params = ()

    status = request.args.get("status")  # optional: /leaves?status=Pending
    if status:
        sql += " WHERE l.status = %s"
        params = (status,)

    return ok(query_all(sql + " ORDER BY l.id", params))


def set_leave_status(leave_id, status):
    ensure_exists("leaves", leave_id, "Leave")
    execute("UPDATE leaves SET status = %s WHERE id = %s", (status, leave_id))
    return ok({"id": leave_id, "status": status}, "Leave status set to " + status)


@app.patch("/leaves/<int:leave_id>/approve")
def approve_leave(leave_id):
    return set_leave_status(leave_id, "Approved")


@app.patch("/leaves/<int:leave_id>/reject")
def reject_leave(leave_id):
    return set_leave_status(leave_id, "Rejected")

# ATTENDANCE

@app.post("/attendance/out")
def mark_out():
    data = get_json()
    require(data, ["student_id", "purpose"])

    student_id = to_int(data["student_id"], "student_id")

    with db_cursor() as cur:
        ensure_exists("students", student_id, "Student", cur)

        cur.execute(
            "SELECT id FROM attendance WHERE student_id = %s AND in_time IS NULL",
            (student_id,),
        )
        if cur.fetchone() is not None:
            raise ApiError("Student already has an active OUT record", 409)

        cur.execute(
            """INSERT INTO attendance (student_id, purpose, out_time, remarks)
               VALUES (%s, %s, NOW(), %s)""",
            (student_id, data["purpose"], data.get("remarks")),
        )
        attendance_id = cur.lastrowid

    return ok({"id": attendance_id}, "OUT recorded", 201)


@app.post("/attendance/in")
def mark_in():
    data = get_json()
    require(data, ["student_id"])

    student_id = to_int(data["student_id"], "student_id")

    with db_cursor() as cur:
        ensure_exists("students", student_id, "Student", cur)

        cur.execute(
            "SELECT id FROM attendance WHERE student_id = %s AND in_time IS NULL",
            (student_id,),
        )
        record = cur.fetchone()

        if record is None:
            raise ApiError("No active OUT record found for this student", 404)

        cur.execute("UPDATE attendance SET in_time = NOW() WHERE id = %s",
                    (record["id"],))

    return ok({"id": record["id"]}, "IN recorded")


@app.get("/attendance")
def list_attendance():
    sql = """SELECT a.id, a.student_id,
                    CONCAT(s.first_name, ' ', s.last_name) AS student_name,
                    a.purpose, a.out_time, a.in_time, a.remarks,
                    IF(a.in_time IS NULL, 'OUTSIDE', 'IN') AS status
             FROM attendance a
             JOIN students s ON s.id = a.student_id"""
    params = ()

    student_id = request.args.get("student_id")  # optional filter
    if student_id:
        sql += " WHERE a.student_id = %s"
        params = (to_int(student_id, "student_id"),)

    return ok(query_all(sql + " ORDER BY a.id DESC", params))

# DASHBOARD

@app.get("/dashboard")
def show_dashboard():
    row = query_one(
        """SELECT
             (SELECT COUNT(*) FROM students)                          AS total_students,
             (SELECT COUNT(*) FROM rooms)                             AS total_rooms,
             (SELECT COUNT(DISTINCT room_id) FROM beds
                WHERE status = 'Available')                           AS available_rooms,
             (SELECT COUNT(*) FROM beds WHERE status = 'Available')   AS available_beds,
             (SELECT COUNT(*) FROM attendance WHERE in_time IS NULL)  AS students_outside,
             (SELECT COUNT(*) FROM leaves WHERE status = 'Pending')   AS pending_leaves,
             (SELECT COUNT(*) FROM visitors WHERE status = 'CheckedIn') AS visitors_inside"""
    )

    row["occupied_rooms"] = row["total_rooms"] - row["available_rooms"]

    return ok(row)

# RUN THE SERVER

if __name__ == "__main__":
    # debug=True auto-restarts on code changes. Use it only while developing.
    app.run(host="127.0.0.1", port=5000, debug=True)