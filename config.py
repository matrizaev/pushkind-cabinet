import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
	SECRET_KEY = os.environ.get('SECRET_KEY') or 'PushkindDotCom'
	ICU_EXTENSION_PATH = os.path.join(basedir, 'libsqliteicu.so')
	SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
	SQLALCHEMY_TRACK_MODIFICATIONS = False
	MAIL_SERVER = os.environ.get ('MAIL_SERVER')
	MAIL_PORT = int(os.environ.get ('MAIL_PORT') or 25)
	MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
	MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
	MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
	ADMINS = ['feedback@tupper.store']
	REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
	REDIS_QUEUE = os.environ.get('REDIS_QUEUE') or 'testing-tasks'