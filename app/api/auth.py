from flask import current_app
from flask_httpauth import HTTPBasicAuth
from app.api.errors import ErrorResponse

basic_auth = HTTPBasicAuth()

@basic_auth.verify_password
def verify_password(username, password):
	return True if password == current_app.config['SECRET_KEY'] else False

@basic_auth.error_handler
def basic_auth_error():
	return ErrorResponse(401)