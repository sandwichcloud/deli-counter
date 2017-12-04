import logging
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

####################
# CORE             #
####################

LOGGING_LEVEL = logging.getLevelName(logging.INFO)
LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S%z'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        }
    },
    'loggers': {
        'deli_counter': {
            'level': LOGGING_LEVEL,
            'handlers': ['console']
        },
        'ingredients_http': {
            'level': LOGGING_LEVEL,
            'handlers': ['console']
        },
        'ingredients_db': {
            'level': LOGGING_LEVEL,
            'handlers': ['console']
        },
        'cherrypy.access': {
            'level': 'INFO',
            'handlers': ['console']
        },
        'cherrypy.error': {
            'level': 'INFO',
            'handlers': ['console']
        },
        'sqlalchemy': {
            'level': 'WARN',
            'handlers': ['console']
        },
        'celery': {
            'level': LOGGING_LEVEL,
            'handlers': ['console']
        },
        'oslo_policy': {
            'level': LOGGING_LEVEL,
            'handlers': ['console']
        }
    }
}

if os.environ.get('CLI'):
    LOGGING_CONFIG['formatters']['default'] = {
        'format': '[%(levelname)s] %(message)s',
        'datefmt': '%Y-%m-%dT%H:%M:%S%z'
    }
    LOGGING_CONFIG['loggers']['alembic'] = {
        'level': LOGGING_LEVEL,
        'handlers': ['console']
    }

####################
# DATABASE         #
####################

DATABASE_DB = 'sandwich'
DATABASE_PORT = '5432'
DATABASE_POOL_SIZE = 20

if os.environ.get('CLI'):
    DATABASE_POOL_SIZE = -1

DATABASE_HOST = os.environ['DATABASE_HOST']
DATABASE_USERNAME = os.environ['DATABASE_USERNAME']
DATABASE_PASSWORD = os.environ['DATABASE_PASSWORD']

####################
# RABBITMQ         #
####################

RABBITMQ_VHOST = '/'
RABBITMQ_PORT = 5672
RABBITMQ_HOST = os.environ['RABBITMQ_HOST']
RABBITMQ_USERNAME = os.environ['RABBITMQ_USERNAME']
RABBITMQ_PASSWORD = os.environ['RABBITMQ_PASSWORD']

####################
# Auth             #
####################

AUTH_DRIVERS = os.environ.get('AUTH_DRIVERS', "deli_counter.auth_drivers.db.driver:DBAuthDriver").split(",")
AUTH_FERNET_KEYS = os.environ['AUTH_FERNET_KEYS'].split(",")

####################
# BUiltIn AUTH     #
####################
# Does builtin auth need any params?

####################
# GITHUB AUTH      #
####################

GITHUB_URL = os.environ.get('GITHUB_URL', 'https://api.github.com')
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
GITHUB_ORG = os.environ.get('GITHUB_ORG')
GITHUB_TEAM_ROLES_PREFIX = os.environ.get("GITHUB_TEAM_ROLES_PREFIX", "sandwich-")

# Split the env var into a dict because it is faster to search
_github_team_roles = os.environ.get('GITHUB_TEAM_ROLES', 'sandwich-admin:admin')
GITHUB_TEAM_ROLES = dict(item.split(":") for item in _github_team_roles.split(","))

####################
# GITLAB AUTH      #
####################
# TODO: implement
GITLAB_URL = os.environ.get('GITLAB_URL', 'https://gitlab.com/api/v4')
GITLAB_CLIENT_ID = os.environ.get('GITLAB_CLIENT_ID')
GITLAB_CLIENT_SECRET = os.environ.get('GITLAB_CLIENT_SECRET')
GITLAB_ORG = os.environ.get('GITLAB_ORG')

####################
# OPENID AUTH      #
####################
# TODO: implement
OPENID_ENDPOINT = os.environ.get('OPENID_ENDPOINT')
OPENID_CLIENT_ID = os.environ.get('OPENID_CLIENT_ID')
OPENID_CLIENT_SECRET = os.environ.get('OPENID_CLIENT_SECRET')
_openid_required_scopes = os.environ.get('OPENID_REQUIRED_SCOPES')
OPENID_REQUIRED_SCOPES = _openid_required_scopes.split(",") if _openid_required_scopes is not None else []

####################
# LDAP AUTH        #
####################
# TODO: implement
LDAP_SERVER = os.environ.get('LDAP_SERVER')
LDAP_USER_DN = os.environ.get('LDAP_USER_DN')
LDAP_ROLE_DB = os.environ.get('LDAP_ROLE_DN')
