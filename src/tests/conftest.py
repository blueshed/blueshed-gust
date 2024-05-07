"""our fixtures"""

import pytest
from blueshed.gust import web


@pytest.fixture(scope='module')
def web_context():
    """reset our context"""
    web.route_map = {}
