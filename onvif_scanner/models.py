from dataclasses import dataclass, field
from typing import List, Optional, Tuple

@dataclass
class StreamProfile:
    name: str
    token: str
    rtsp_uri: str

@dataclass
class PTZStatus:
    pan: float
    tilt: float
    zoom: float

@dataclass
class PTZLimits:
    pan: Tuple[float, float]
    tilt: Tuple[float, float]
    zoom: Tuple[float, float]

@dataclass
class PTZInfo:
    supported: bool
    status: Optional[PTZStatus] = None
    limits: Optional[PTZLimits] = None

@dataclass
class CameraInfo:
    ip: str
    manufacturer: str
    model: str
    firmware: str
    serial: str
    profiles: List[StreamProfile] = field(default_factory=list)
    ptz: Optional[PTZInfo] = None
