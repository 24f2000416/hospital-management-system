from flask import Blueprint, render_template
routes_admin = Blueprint('routes_admin', __name__)

@routes_admin.route('/')
def admin_dashboard():
    return render_template('adrr.html')