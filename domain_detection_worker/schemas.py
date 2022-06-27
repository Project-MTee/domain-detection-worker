import json
from typing import Union

from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder


class Request(BaseModel):
    """
    A dataclass that can be used to store requests
    """
    text: Union[str, list]
    src: str


@dataclass
class Response:
    """
    A dataclass that can be used to store responses and transfer them over the message queue if needed.
    """
    domain: str

    def encode(self) -> bytes:
        return json.dumps(self, default=pydantic_encoder).encode()
