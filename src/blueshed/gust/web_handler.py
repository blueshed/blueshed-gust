"""We handle http methods"""

import logging

from tornado.util import unicode_type
from tornado.web import HTTPError, RequestHandler

from .utils import Redirect, UserMixin

log = logging.getLogger(__name__)


class WebHandler(UserMixin, RequestHandler):
    """We handle the method"""

    def initialize(self, method_settings):
        """setup variables"""
        self.method_settings = method_settings

    def set_default_headers(self):
        """if in debug mode allow cors"""
        if self.settings.get('debug', False):
            self.set_header('Access-Control-Allow-Origin', '*')
            self.set_header('Access-Control-Allow-Headers', 'x-requested-with')
            self.set_header(
                'Access-Control-Allow-Methods',
                'PUT, DELETE, POST, GET, OPTIONS, HEAD',
            )
        else:
            super().set_default_headers()

    async def prepare(self):
        """
        prepare can be either sync or async according
        to the tornado code and documentation.
        """
        method = self.request.method.lower()
        settings = getattr(self.method_settings, method)
        if not settings:
            return

        template, auth = settings.template, settings.auth
        if auth and self.current_user is None:
            self.not_authenticated()

        try:
            result = await self.application.perform(
                self, self.current_user, settings.func, self
            )
            log.debug('http outcome: %s', result)
        except Redirect as ex:
            self.redirect(ex.url)
            return
        except Exception as ex:
            log.exception(settings.func)
            raise HTTPError(500) from ex

        # of course if we throw and exception
        # it will be written out as an error page
        if template:
            assert isinstance(
                result, dict
            ), f'Templates require dicts to render, got {result!r}!'
            self.render(template, **result)
            # render calls finish for us.
        else:
            if not isinstance(result, (bytes, unicode_type, dict)):
                result = {'result': result}
            if result is not None:
                self.write(result)
            self.finish()
