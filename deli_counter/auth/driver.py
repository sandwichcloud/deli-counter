import logging
from abc import ABCMeta, abstractmethod
from typing import Dict

from ingredients_http.router import Router


class AuthDriver(object):
    __metaclass__ = ABCMeta

    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))

    @abstractmethod
    def discover_options(self) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def auth_router(self) -> Router:
        raise NotImplementedError
