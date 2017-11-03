####################
# CORE             #
####################
import logging

DEBUG = False
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

####################
# RABBITMQ         #
####################

# TODO: Calls to rabbitmq will be mocked out
RABBITMQ_VHOST = '/'
RABBITMQ_PORT = 5672
RABBITMQ_HOST = '127.0.0.1'
RABBITMQ_USERNAME = 'guest'
RABBITMQ_PASSWORD = 'guest'

####################
# Auth             #
####################

AUTH_DRIVERS = [
    # 'deli_counter.auth.drivers.db.driver:DBAuthDriver',
    'deli_counter.auth.drivers.github.driver:GithubAuthDriver'
]

####################
# GITHUB AUTH      #
####################

# API calls will be mocked so having a fake client id/secret is fine
GITHUB_URL = 'https://api.github.com'
GITHUB_CLIENT_ID = 'GITHUB_CLIENT_ID'
GITHUB_CLIENT_SECRET = 'GITHUB_CLIENT_SECRET'
GITHUB_ORG = 'sandwich'
GITHUB_TEAM_ROLES = {
    "sandwich-admin": "admin"
}
GITHUB_TEAM_ROLES_PREFIX = "sandwich-"
