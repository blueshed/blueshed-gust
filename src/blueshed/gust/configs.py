"""our configuration dataclasses"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class WebMethod:
    """the function to be called on this method"""

    func: str
    template: str = None
    auth: bool = False


@dataclass
class WebConfig:
    """possible methods:"""

    get: WebMethod = None
    post: WebMethod = None
    put: WebMethod = None
    delete: WebMethod = None
    head: WebMethod = None


@dataclass
class WsConfig:
    """
    functions to be called on websocket events
    on_rpc functions will be made public
    """

    ws_message: WebMethod = None
    ws_open: WebMethod = None
    ws_close: WebMethod = None
    ws_rpc: Dict[str, WebMethod] = field(default_factory=dict)
    auth: bool = False
