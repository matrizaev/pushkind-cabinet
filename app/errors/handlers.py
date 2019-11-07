from flask import render_template, request
from app.errors import bp
from app import db
from app.api.errors import ErrorResponse as ApiErrorResponse


def WantsJsonResponse():
    return request.accept_mimetypes['application/json'] >= \
        request.accept_mimetypes['text/html']


@bp.app_errorhandler(404)
def NotFoundError(error):
	if WantsJsonResponse():
		return ApiErrorResponse(404)
	return render_template('errors/404.html'), 404
	
	
@bp.app_errorhandler(500)
def InternalError(error):
	db.session.rollback()
	if WantsJsonResponse():
		return ApiErrorResponse(500)
	return render_template('errors/500.html'), 500