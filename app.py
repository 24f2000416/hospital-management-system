from flask import Flask
from flask_login import LoginManager
from flask_jwt_extended import JWTManager

from models import db, User
from config import Config
from routes import routes
from routes_admin import routes_admin


app = Flask(__name__)

app.config.from_object(Config)

jwt = JWTManager(app)




if not app.config.get("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY environment variable is not set")



database_url = app.config.get("SQLALCHEMY_DATABASE_URI")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

# Use psycopg2 dialect (psycopg2-binary is installed)
if database_url and database_url.startswith("postgresql://") and "+psycopg" not in database_url:
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = (
    database_url or "sqlite:///hospital.db"
)




db.init_app(app)




login_manager = LoginManager()
login_manager.init_app(app)

# If a logged-out user tries to access @login_required
# they will be redirected to your login page.
login_manager.login_view = "routes.login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


from flask import session

@app.after_request
def add_jwt_header(response):
    jwt_token = session.get('jwt_token')
    if jwt_token:
        response.headers['X-JWT-Token'] = jwt_token
    return response


app.register_blueprint(routes)
app.register_blueprint(routes_admin)



from werkzeug.security import generate_password_hash

with app.app_context():

    db.create_all()

    admin_username = app.config.get("ADMIN_USERNAME")
    admin_email = app.config.get("ADMIN_EMAIL")
    admin_password = app.config.get("ADMIN_PASSWORD")

    if not admin_username:
        raise RuntimeError("ADMIN_USERNAME is not configured.")

    if not admin_email:
        raise RuntimeError("ADMIN_EMAIL is not configured.")

    if not admin_password:
        raise RuntimeError("ADMIN_PASSWORD is not configured.")

    existing_admin = User.query.filter_by(
        username=admin_username
    ).first()

    if existing_admin is None:

        admin = User(
            username=admin_username,
            email=admin_email,
            password=generate_password_hash(admin_password),
            role="admin",
            phone="1000000000"
        )

        db.session.add(admin)
        db.session.commit()

        print("Default admin created.")

    else:

        print("Admin already exists. Skipping admin creation.")



if __name__ == "__main__":
    app.run(debug=True)