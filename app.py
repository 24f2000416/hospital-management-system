from flask import Flask
from models import db
import os

from routes import routes
from routes_admin import routes_admin


app = Flask(__name__)


app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key"
)



database_url = os.environ.get("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = (
    database_url or "sqlite:///hospital.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False




db.init_app(app)




app.register_blueprint(routes)
app.register_blueprint(routes_admin)



with app.app_context():

    db.create_all()

    from models import User

    # Create default admin if no admin exists
    if not User.query.filter_by(role="admin").first():

        admin = User(
            username=os.environ.get(
                "ADMIN_USERNAME",
                "admin"
            ),

            email=os.environ.get(
                "ADMIN_EMAIL",
                "admin@example.com"
            ),

            password=os.environ.get(
                "ADMIN_PASSWORD",
                "admin123"
            ),

            role="admin",

            phone="1000000000"
        )

        db.session.add(admin)
        db.session.commit()

        print("Default admin created!")



if __name__ == "__main__":
    app.run(debug=True)