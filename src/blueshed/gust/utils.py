"""Authentication"""

import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, Union
from urllib.parse import urlencode

from tornado.web import HTTPError

from . import json_utils


class Redirect(Exception):
    """redirect to url and if cookie set it"""

    def __init__(self, url='/'):
        self.url = url
        super().__init__()


class JsonRpcException(Exception):
    """Throw xception that captures message"""

    def __init__(self, code, message):
        super().__init__(self, message)
        self.js_code = code
        self.js_message = message

    def to_json(self):
        """serialize for json"""
        return {'code': self.js_code, 'message': self.js_message}


@dataclass
class JsonRpcResponse:
    """
    return from a procdure call
    """

    id: Union[str, int]
    result: Dict
    error: Any
    jsonrpc: str = '2.0'

    def __post_init__(self):
        """stringify error"""
        if self.error:
            if isinstance(self.error, JsonRpcException):
                self.error = self.error.to_json()
            else:
                self.error = str(self.error)


class UserMixin:
    """Support for user in tornado handlers"""

    @property
    def cookie_name(self):
        """return the cookie_name declared in application settings"""
        return self.settings.get('cookie_name')

    def get_current_user(self):
        """return the current user from the cookie"""
        result = None
        if self.cookie_name:
            result = self.get_secure_cookie(self.cookie_name)
            if result:
                result = json_utils.loads(result.decode('utf-8'))
        return result

    def set_current_user(self, value):
        """put the current user in the cookie"""
        if value:
            self.set_secure_cookie(self.cookie_name, json_utils.dumps(value))
        else:
            self.clear_cookie(self.cookie_name)

    def not_authenticated(self):
        """raise a redirect or error, tornado code dug out of a wrapper"""
        if self.request.method in ('GET', 'HEAD'):
            url = self.get_login_url()
            if '?' not in url:
                if urllib.parse.urlsplit(url).scheme:
                    # if login url is absolute, make next absolute too
                    next_url = self.request.full_url()
                else:
                    assert self.request.uri is not None
                    next_url = self.request.uri
                url += '?' + urlencode({'next': next_url})
            self.redirect(url)
            return None
        raise HTTPError(403)
