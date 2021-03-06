from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES


def ErrorResponse(status_code, message=None):
	payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
	if message:
		payload['message'] = message
	response = jsonify(payload)
	response.status_code = status_code
	return response


def BadRequest(message):
	return ErrorResponse(400, message)