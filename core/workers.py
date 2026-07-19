"""
NOCPing — core/workers.py
QThread workers que executam operações de rede e emitem sinais PyQt6.
"""
import itertools
import os
import threading
import socket as _socket

from PyQt6.QtCore import QThread, pyqtSignal

from .models import PingResult, ProbeConfig, ProbeMode, IPVersion
from .network import (
    resolve_host, tcp_ping_once, icmp_ping_once, udp_ping_once,
    scan_ports, banner_grab, _parse_ports, calc_stats, is_admin,
    traceroute_hop,
)

# PID ICMP único por worker (não por thread OS — o Windows recicla thread IDs
# entre QThreads de vida curta, o que pode colidir com o de outro worker vivo).
_icmp_pid_counter = itertools.count(1)
_icmp_pid_lock = threading.Lock()


def _next_icmp_pid() -> int:
    with _icmp_pid_lock:
        return next(_icmp_pid_counter) & 0xFFFF


class PingWorker(QThread):
    """Worker de ping contínuo (TCP / ICMP / UDP)."""

    result   = pyqtSignal(object)   # PingResult
    resolved = pyqtSignal(str, str) # (ip, version_label)
    stats    = pyqtSignal(dict)     # estatísticas finais
    error    = pyqtSignal(str)

    def __init__(self, config: ProbeConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._stop = threading.Event()
        self._ip = None
        self._family = None
        self._pid = _next_icmp_pid()

    def stop(self):
        self._stop.set()

    def run(self):
        cfg = self.config
        try:
            family, ip = resolve_host(cfg.host, cfg.port, cfg.ip_version)
        except OSError as e:
            self.error.emit(f"Resolve falhou: {e}")
            return

        self._family = family
        self._ip = ip
        version_label = "IPv6" if family == _socket.AF_INET6 else "IPv4"
        self.resolved.emit(ip, version_label)

        if cfg.mode in (ProbeMode.ICMP, ProbeMode.UDP) and not is_admin():
            self.error.emit(
                f"Modo {cfg.mode.value} requer privilégios de Administrador."
            )
            return

        results = []
        seq = 0

        while not self._stop.is_set():
            seq += 1
            try:
                if cfg.mode == ProbeMode.TCP:
                    r = tcp_ping_once(
                        ip, cfg.port, family,
                        timeout_ms=cfg.timeout_ms,
                        length=cfg.payload_length,
                        dont_fragment=cfg.dont_fragment,
                    )
                    r = PingResult(seq, r.success, r.elapsed_ms, r.note)
                elif cfg.mode == ProbeMode.ICMP:
                    r = icmp_ping_once(
                        ip, family, seq, self._pid,
                        timeout_ms=cfg.timeout_ms,
                        length=cfg.payload_length or None,
                        dont_fragment=cfg.dont_fragment,
                    )
                else:  # UDP
                    r = udp_ping_once(
                        ip, cfg.port, family, seq,
                        timeout_ms=cfg.timeout_ms,
                        length=cfg.payload_length,
                        dont_fragment=cfg.dont_fragment,
                    )
            except PermissionError:
                self.error.emit(
                    f"Permissão negada para {cfg.mode.value}. Execute como Administrador."
                )
                return
            except Exception as e:
                r = PingResult(seq, False, 0.0, str(e))

            results.append(r)
            self.result.emit(r)

            if cfg.count > 0 and seq >= cfg.count:
                break

            # Aguarda intervalo — acorda imediatamente se stop() for chamado
            self._stop.wait(timeout=cfg.interval_ms / 1000.0)
            if self._stop.is_set():
                break

        self.stats.emit(calc_stats(results))


class ScanWorker(QThread):
    """Worker de port scan multithread."""

    port_result = pyqtSignal(int, bool, float, str)  # porta, aberta, ms, protocolo
    progress    = pyqtSignal(int, int)                # done, total
    finished_ok = pyqtSignal()
    error       = pyqtSignal(str)

    def __init__(self, host: str, port_spec: str, ip_version: IPVersion,
                 timeout_ms: int = 200, max_threads: int = 200,
                 protocol: str = "TCP", parent=None):
        super().__init__(parent)
        self.host = host
        self.port_spec = port_spec
        self.ip_version = ip_version
        self.timeout_ms = timeout_ms
        self.max_threads = max_threads
        self.protocol = protocol
        self._stop = threading.Event()
        self._done = 0
        self._lock = threading.Lock()

    def stop(self):
        self._stop.set()

    def run(self):
        try:
            family, ip = resolve_host(self.host, 80, self.ip_version)
        except OSError as e:
            self.error.emit(f"Resolve falhou: {e}")
            return

        try:
            ports = _parse_ports(self.port_spec)
        except ValueError as e:
            self.error.emit(f"Portas inválidas: {e}")
            return

        multiplier = 2 if self.protocol == "TCP+UDP" else 1
        total = len(ports) * multiplier
        self._done = 0

        def on_result(port, is_open, ms, proto):
            with self._lock:
                self._done += 1
                done = self._done
            self.port_result.emit(port, is_open, ms, proto)
            self.progress.emit(done, total)

        scan_ports(
            ip, family, ports,
            timeout_ms=self.timeout_ms,
            on_result=on_result,
            stop_event=self._stop,
            max_threads=self.max_threads,
            protocol=self.protocol,
        )
        self.finished_ok.emit()


def _resolve_hostname(ip: str, timeout: float = 2.0) -> str:
    """Resolve DNS reverso com timeout — helper compartilhado."""
    result = [ip]
    def _dns():
        try:
            result[0] = _socket.gethostbyaddr(ip)[0]
        except Exception:
            pass
    t = threading.Thread(target=_dns, daemon=True)
    t.start()
    t.join(timeout=timeout)
    return result[0]


class TracerouteWorker(QThread):
    """Worker de traceroute ICMP (requer admin)."""

    hop      = pyqtSignal(dict)   # {ttl, from_ip, hostname, elapsed_ms, timeout, destination_reached, error}
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, host: str, ip_version: IPVersion,
                 max_hops: int = 30, timeout_ms: int = 2000, parent=None):
        super().__init__(parent)
        self.host = host
        self.ip_version = ip_version
        self.max_hops = max_hops
        self.timeout_ms = timeout_ms
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        if not is_admin():
            self.error.emit(
                "Traceroute requer privilégios de Administrador (raw socket ICMP)."
            )
            return

        try:
            family, ip = resolve_host(self.host, 0, self.ip_version)
        except OSError as e:
            self.error.emit(f"Resolve falhou: {e}")
            return

        pid = _next_icmp_pid()

        for ttl in range(1, self.max_hops + 1):
            if self._stop.is_set():
                break

            hop = traceroute_hop(ip, family, ttl, ttl, pid, self.timeout_ms)

            if hop["from_ip"] and not hop["timeout"]:
                hostname = _resolve_hostname(hop["from_ip"])
            else:
                hostname = None
            hop["hostname"] = hostname

            self.hop.emit(hop)

            if hop.get("error") == "permission":
                self.error.emit(
                    "Permissão negada. Execute como Administrador."
                )
                return
            if hop["destination_reached"]:
                break

        self.finished.emit()


class MTRWorker(QThread):
    """Worker de MTR contínuo (My TraceRoute — requer admin)."""

    hop_discovered = pyqtSignal(int, str, str)   # ttl, ip, hostname
    hop_update     = pyqtSignal(int, dict)        # ttl, stats
    status         = pyqtSignal(str)
    finished       = pyqtSignal()
    error          = pyqtSignal(str)

    def __init__(self, host: str, ip_version: IPVersion,
                 max_hops: int = 30, timeout_ms: int = 1000,
                 interval_ms: int = 200, parent=None):
        super().__init__(parent)
        self.host = host
        self.ip_version = ip_version
        self.max_hops = max_hops
        self.timeout_ms = timeout_ms
        self.interval_ms = interval_ms
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        import statistics as _stats
        if not is_admin():
            self.error.emit("MTR requer privilégios de Administrador (raw socket ICMP).")
            return
        try:
            family, ip = resolve_host(self.host, 0, self.ip_version)
        except OSError as e:
            self.error.emit(f"Resolve falhou: {e}")
            return

        pid = _next_icmp_pid()
        seq = 0
        per_hop: dict[int, dict] = {}  # ttl -> {sent, received, rtts, ip, hostname}
        current_max = self.max_hops

        while not self._stop.is_set():
            for ttl in range(1, current_max + 1):
                if self._stop.is_set():
                    break

                seq = (seq + 1) & 0xFFFF
                hop = traceroute_hop(ip, family, ttl, seq, pid, self.timeout_ms)

                if hop.get("error") == "permission":
                    self.error.emit("Permissão negada. Execute como Administrador.")
                    return

                from_ip = hop["from_ip"] or ""

                if ttl not in per_hop:
                    hostname = _resolve_hostname(from_ip) if from_ip else from_ip
                    per_hop[ttl] = {"sent": 0, "received": 0, "rtts": [],
                                    "ip": from_ip, "hostname": hostname}
                    self.hop_discovered.emit(ttl, from_ip, hostname)
                elif from_ip and not per_hop[ttl]["ip"]:
                    hostname = _resolve_hostname(from_ip)
                    per_hop[ttl]["ip"] = from_ip
                    per_hop[ttl]["hostname"] = hostname
                    self.hop_discovered.emit(ttl, from_ip, hostname)

                s = per_hop[ttl]
                s["sent"] += 1
                if not hop["timeout"] and from_ip:
                    s["received"] += 1
                    s["rtts"].append(hop["elapsed_ms"])

                sent = s["sent"]
                received = s["received"]
                rtts = s["rtts"]
                loss_pct = (sent - received) / sent * 100 if sent else 0.0
                self.hop_update.emit(ttl, {
                    "loss_pct":  loss_pct,
                    "sent":      sent,
                    "last_ms":   rtts[-1] if rtts else 0.0,
                    "avg_ms":    _stats.mean(rtts) if rtts else 0.0,
                    "best_ms":   min(rtts) if rtts else 0.0,
                    "worst_ms":  max(rtts) if rtts else 0.0,
                    "stdev_ms":  _stats.stdev(rtts) if len(rtts) > 1 else 0.0,
                })

                if hop["destination_reached"]:
                    current_max = ttl
                    break

            # Wait AFTER completing full cycle, not between each hop
            self._stop.wait(self.interval_ms / 1000.0)

        self.finished.emit()


class BannerWorker(QThread):
    """Worker de banner grab + TLS."""

    result = pyqtSignal(dict)
    error  = pyqtSignal(str)

    def __init__(self, host: str, port: int, ip_version: IPVersion,
                 timeout_ms: int = 2000, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.ip_version = ip_version
        self.timeout_ms = timeout_ms

    def run(self):
        try:
            family, ip = resolve_host(self.host, self.port, self.ip_version)
        except OSError as e:
            self.error.emit(f"Resolve falhou: {e}")
            return

        data = banner_grab(ip, self.port, family, self.timeout_ms)
        if data.get("error") and not data.get("connected"):
            self.error.emit(data["error"])
        else:
            self.result.emit(data)
