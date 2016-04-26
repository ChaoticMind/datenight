import logging

from flask import render_template, request

from server import app, socketio

log = logging.getLogger(__name__)


@app.route('/')
def index():
	return render_template('index.html')


@app.route('/control')
def control():
	return render_template('control.html')


@socketio.on_error_default
def default_error_handler(e):
	log.critical(request.event["message"])
	log.critical(request.event["args"])
	raise
