from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# My App
app = Flask(__name__)


@app.route("/")
def index():
    return "Test 123"


if __name__ in "__main__":
    app.run(debug=True)
