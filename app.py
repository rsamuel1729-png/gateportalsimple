import os
from functools import wraps
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret")
client = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=3000)
client.admin.command("ping")
mongo = client[os.getenv("MONGO_DB", "gate_prep")]
mongo.users.create_index("email", unique=True)
COURSES = [
    ("engineering-mathematics", "Engineering Mathematics", "Discrete math and probability."),
    ("digital-logic", "Digital Logic", "Boolean algebra and circuits."),
    ("computer-organization", "Computer Organization & Architecture", "Processors and memory."),
    ("programming-data-structures", "Programming & Data Structures", "C programming and data structures."),
    ("algorithms", "Algorithms", "Searching, sorting and graph algorithms."),
    ("toc-compiler-design", "Theory of Computation & Compiler Design", "Automata and parsing."),
    ("operating-systems", "Operating Systems", "Processes, memory and files."),
    ("dbms-networks", "Databases & Computer Networks", "SQL, networks and protocols.")]
TYPES = {"website": "Website", "video": "Video"}
admin_email = os.getenv("ADMIN_EMAIL", "admin@gate.local").lower()
if not mongo.users.find_one({"email": admin_email}):
    mongo.users.insert_one({"name": "Administrator", "email": admin_email,
        "password_hash": generate_password_hash(os.getenv("ADMIN_PASSWORD", "admin123")), "role": "admin"})

def records(items): return [dict(item, id=str(item["_id"])) for item in items]
def need(role=None):
    def decorate(view):
        @wraps(view)
        def check(*args, **kwargs):
            if not session.get("user_id"): return redirect(url_for("login"))
            if role and session.get("role") != role: abort(403)
            return view(*args, **kwargs)
        return check
    return decorate
@app.route("/")
def index():
    if session.get("role"): return redirect(url_for("admin" if session["role"] == "admin" else "courses"))
    return render_template("index.html", courses=COURSES)
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name, email, password = (request.form.get(k, "").strip() for k in ("name", "email", "password"))
        if not name or "@" not in email or len(password) < 6:
            flash("Enter a name, valid email and password of 6+ characters.", "error")
        else:
            try:
                user = {
                    "name": name, "email": email.lower(),
                    "password_hash": generate_password_hash(password), "role": "user"
                }
                session.update(user_id=str(mongo.users.insert_one(user).inserted_id), name=name, role="user")
                return redirect(url_for("courses"))
            except DuplicateKeyError: flash("Email already registered.", "error")
    return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = {"admin": "admin", "student": "user"}.get(request.form.get("account_type"))
        user = mongo.users.find_one({"email": request.form.get("email", "").strip().lower()})
        valid_password = user and check_password_hash(
            user["password_hash"], request.form.get("password", "")
        )
        if role and user and user["role"] == role and valid_password:
            session.clear(); session.update(user_id=str(user["_id"]), name=user["name"], role=role)
            return redirect(url_for("admin" if role == "admin" else "courses"))
        flash("Check account type, email, and password.", "error")
    return render_template("login.html")
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
@app.route("/courses")
@need("user")
def courses():
    counts = {c[1]: mongo.materials.count_documents({"subject": c[1]}) for c in COURSES}
    return render_template("courses.html", courses=COURSES, counts=counts)
@app.route("/courses/<course_name>")
@need("user")
def course(course_name):
    selected = next((c for c in COURSES if c[0] == course_name), None)
    if not selected: abort(404)
    items = records(mongo.materials.find({"subject": selected[1]}).sort("title", ASCENDING))
    return render_template("course.html", course=selected, materials=items, resource_types=TYPES)
@app.route("/admin")
@need("admin")
def admin():
    materials = records(mongo.materials.find().sort("_id", -1))
    return render_template("admin.html", materials=materials, resource_types=TYPES)
@app.route("/admin/material/new", methods=["GET", "POST"])
@app.route("/admin/material/<item_id>/edit", methods=["GET", "POST"])
@need("admin")
def resource_form(item_id=None):
    item = None
    if item_id and ObjectId.is_valid(item_id):
        item = mongo.materials.find_one({"_id": ObjectId(item_id)})
    if item_id and not item: abort(404)
    if request.method == "POST":
        values = {
            "title": request.form.get("title", "").strip(),
            "subject": request.form.get("subject", ""),
            "description": request.form.get("description", "").strip(),
            "url": request.form.get("url", "").strip(),
            "resource_type": request.form.get("resource_type", "")
        }
        valid_resource = (
            values["title"] and values["description"]
            and values["url"].startswith(("https://", "http://"))
            and values["subject"] in [c[1] for c in COURSES]
            and values["resource_type"] in TYPES
        )
        if not valid_resource:
            flash("Complete all fields and choose a valid course and type.", "error")
        else:
            if item: mongo.materials.update_one({"_id": item["_id"]}, {"$set": values})
            else: mongo.materials.insert_one(values)
            return redirect(url_for("admin"))
    item = records([item])[0] if item else None
    return render_template("material_form.html", material=item, courses=COURSES, resource_types=TYPES)
@app.post("/admin/material/<item_id>/delete")
@need("admin")
def delete_resource(item_id):
    if not ObjectId.is_valid(item_id): abort(404)
    mongo.materials.delete_one({"_id": ObjectId(item_id)})
    return redirect(url_for("admin"))
if __name__ == "__main__": app.run(debug=True)
