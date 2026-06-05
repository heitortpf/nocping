from dataclasses import dataclass
from enum import Enum, auto


class ProbeMode(Enum):
    TCP = "TCP"
    ICMP = "ICMP"
    UDP = "UDP"


class IPVersion(Enum):
    AUTO = "Auto"
    IPV4 = "IPv4"
    IPV6 = "IPv6"


class HostStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    UP = auto()
    DOWN = auto()
    ERROR = auto()


@dataclass
class PingResult:
    seq: int
    success: bool
    elapsed_ms: float = 0.0
    note: str = ""


@dataclass
class ProbeConfig:
    host: str
    port: int = 80
    mode: ProbeMode = ProbeMode.TCP
    ip_version: IPVersion = IPVersion.AUTO
    count: int = 0          # 0 = infinito
    timeout_ms: int = 2000
    interval_ms: int = 1000
    payload_length: int = 0 # 0 = padrão
    dont_fragment: bool = False
