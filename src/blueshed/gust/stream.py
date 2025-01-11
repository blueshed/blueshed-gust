import uuid
from typing import AsyncGenerator


class Stream:
    """A special instance of a result after a result"""

    def __init__(self, gen: AsyncGenerator) -> None:
        self.id = str(uuid.uuid4())
        self.gen = gen

    def to_json(self) -> dict:
        """We're just a response"""
        return {'stream_id': self.id}
