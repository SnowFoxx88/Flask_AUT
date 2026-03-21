from flask import Flask, render_template, redirect, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user
from datetime import datetime, timezone
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_required, current_user, LoginManager, logout_user
import os
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# 1. APP CONFIGURATION
app = Flask(__name__)

# The secret_key is like a 'password' for your app to secure cookies/sessions
app.secret_key = os.getenv("SECRET_KEY")

# Tell SQLAlchemy where our database file is located (SQLite creates a local file)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the Database and Login Manager
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Tell Flask-Login where to send users if they try to access a protected page (name must match function name)
login_manager.login_view = "login"

###################################### DATA MODELS ######################################
# Models define the structure of your database tables


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    # We store the 'hashed' version of the password, never the plain text
    password = db.Column(db.String(80), nullable=False)
    # 'tasks' is a relationship, not a column. It allows User.tasks to work.
    tasks = db.relationship("MyTask", backref="owner", lazy=True)


class MyTask(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(100), nullable=False)
    complete = db.Column(db.Integer)
    # Use timezone-aware UTC time to avoid confusion between timezones
    created = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    # Foreign Key connects a task to a specific user via their ID
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __repr__(self) -> str:
        return f"Task {self.id}"


###################################### AUTHENTICATION ######################################
# This function helps Flask-Login load the user from their ID stored in a cookie
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


###################################### ROUTES ######################################


# Register page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check if the name exists to avoid a crash from the 'unique=True' constraint
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("That username is already taken.")
            return redirect("/register")

        # Hash the password (turns '123' into a long random string)
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)

        try:
            db.session.add(new_user)  # Stage the user
            db.session.commit()  # Save to database
            flash("Registration successful! Please log in.")
            return redirect("/login")
        except Exception as e:
            print(f"ERROR: {e}")
            return f"ERROR: {e}"
    else:
        # 'render_template' takes the HTML file and sends it to the user's browser.
        # It automatically looks inside the 'templates/' folder to find the file.
        return render_template("register.html")


# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        # check_password_hash compares the typed password with the hashed version
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect("/")
        else:
            flash("Invalid username or password.")

    return render_template("login.html")


# Home page
@app.route("/", methods=["POST", "GET"])
@login_required  # Prevents strangers from seeing this page (by entering this ressource (GET))
def index():
    # Add a Task
    if request.method == "POST":
        current_task = request.form["content"]
        new_task = MyTask(content=current_task, user_id=current_user.id)  # Create a task linked specifically to the logged-in user
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect("/")
        except Exception as e:
            print(f"ERROR: {e}")
            return f"ERROR: {e}"
    else:
        # Only pull tasks belonging to the current_user, sorted by time
        tasks = MyTask.query.filter_by(user_id=current_user.id).order_by(MyTask.created).all()
        return render_template("index.html", tasks=tasks)


# Delete an item
@app.route("/delete/<int:id>")
@login_required
def delete(id: int):
    # get_or_404 shows a 'Not Found' page if the ID doesn't exist
    delete_task = MyTask.query.get_or_404(id)
    try:
        db.session.delete(delete_task)
        db.session.commit()
        return redirect("/")
    except Exception as e:
        return f"ERROR: {e}"


# Edit an item
@app.route("/edit/<int:id>", methods=["POST", "GET"])
@login_required
def edit(id: int):
    task = MyTask.query.get_or_404(id)
    if request.method == "POST":
        task.content = request.form["content"]
        try:
            db.session.commit()
            return redirect("/")
        except Exception as e:
            return f"ERROR: {e}"
    else:
        return render_template("edit.html", task=task)


@app.route("/logout")
@login_required  # Only logged-in people can logout
def logout():
    logout_user()  # This removes the 'I am logged in' cookie from the browser
    flash("You have been logged out.")
    return redirect("/login")  # Send them back to the login page


# Runner and Debugger
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # This creates the .db file and tables if they don't exist

    app.run(debug=True)
