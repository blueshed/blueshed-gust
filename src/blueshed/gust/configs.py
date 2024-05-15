"""our configuration dataclasses"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class WebMethod:
    """the function to be called on this method"""

    func: str
    template: Optional[str] = None
    auth: bool = False


@dataclass
class WebConfig:
    """possible methods:"""

    get: Optional[WebMethod] = None
    post: Optional[WebMethod] = None
    put: Optional[WebMethod] = None
    delete: Optional[WebMethod] = None
    head: Optional[WebMethod] = None


@dataclass
class WsConfig:
    """
    functions to be called on websocket events
    on_rpc functions will be made public
    """

    ws_message: Optional[WebMethod] = None
    ws_open: Optional[WebMethod] = None
    ws_close: Optional[WebMethod] = None
    ws_rpc: Dict[str, WebMethod] = field(default_factory=dict)
    auth: bool = False
