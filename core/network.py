"""
NOCPing — core/network.py
Funções de rede puras: sem GUI, sem saída no terminal.
"""
import asyncio
import os
import socket
import struct
import select
import ssl
import time
import threading
import statistics
from typing import Callable, Optional

from .models import PingResult, IPVersion


# ---------------------------------------------------------------------------
# Privilégios
# ---------------------------------------------------------------------------

def is_admin() -> bool:
    if os.name == "nt":
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    else:
        return os.getuid() == 0


# ---------------------------------------------------------------------------
# Resolução de host
# ---------------------------------------------------------------------------

def resolve_host(host: str, port: int, ip_version: IPVersion) -> tuple:
    """Retorna (family, ip_str) ou lança OSError."""
    if ip_version == IPVersion.IPV4:
        family_filter = socket.AF_INET
    elif ip_version == IPVersion.IPV6:
        family_filter = socket.AF_INET6
    else:
        family_filter = socket.AF_UNSPEC

    infos = socket.getaddrinfo(host, port, family_filter, socket.SOCK_STREAM)
    if not infos:
        raise OSError(f"Não foi possível resolver '{host}'")
    af, _, _, _, sa = infos[0]
    ip = sa[0]
    return af, ip


# ---------------------------------------------------------------------------
# Don't Fragment — cross-platform
# ---------------------------------------------------------------------------

def set_dont_fragment(sock: socket.socket, family: int) -> None:
    try:
        if os.name == "nt":
            sock.setsockopt(socket.IPPROTO_IP, 14, 1)
        elif sys.platform == "darwin":
            IP_DONTFRAG = 67
            if family == socket.AF_INET:
                sock.setsockopt(socket.IPPROTO_IP, IP_DONTFRAG, 1)
        else:
            if family == socket.AF_INET:
                sock.setsockopt(socket.IPPROTO_IP,
                                socket.IP_MTU_DISCOVER,
                                socket.IP_PMTUDISC_DO)
            elif family == socket.AF_INET6:
                IPV6_MTU_DISCOVER = 23
                IP_PMTUDISC_DO = 2
                sock.setsockopt(socket.IPPROTO_IPV6, IPV6_MTU_DISCOVER, IP_PMTUDISC_DO)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# ICMP helpers
# ---------------------------------------------------------------------------

def _checksum(data: bytes) -> int:
    s = 0
    for i in range(0, len(data) - 1, 2):
        s += (data[i] << 8) + data[i + 1]
    if len(data) % 2:
        s += data[-1] << 8
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return ~s & 0xFFFF


def _build_icmp_echo(seq: int, pid: int, is_ipv6: bool,
                     length: Optional[int] = None) -> bytes:
    type_val = 128 if is_ipv6 else 8
    hdr = struct.pack("!BBHHH", type_val, 0, 0, pid & 0xFFFF, seq & 0xFFFF)
    payload = b"nocping" + bytes(range(25)) if length is None else b"A" * length
    if is_ipv6:
        return hdr + payload
    data = hdr + payload
    chk = _checksum(data)
    return struct.pack("!BBHHH", type_val, 0, chk, pid & 0xFFFF, seq & 0xFFFF) + payload


def _icmp_type(data: bytes, family: int) -> int:
    try:
        if family == socket.AF_INET:
            ihl = (data[0] & 0x0F) * 4
            return data[ihl]
        return data[0]
    except IndexError:
        return -1


# ---------------------------------------------------------------------------
# TCP ping (uma tentativa)
# ---------------------------------------------------------------------------

def tcp_ping_once(ip: str, port: int, family: int,
                  timeout_ms: int = 2000,
                  length: int = 0,
                  dont_fragment: bool = False) -> PingResult:
    seq = 0
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        if dont_fragment:
            set_dont_fragment(sock, family)
        sock.settimeout(timeout_ms / 1000.0)
        t0 = time.perf_counter()
        err = sock.connect_ex((ip, port))
        ms = (time.perf_counter() - t0) * 1000

        if err == 0:
            if length > 0:
                try:
                    sock.sendall(b"A" * length)
                except OSError:
                    pass
            return PingResult(seq, True, ms)
        elif err in (111, 10061):
            return PingResult(seq, True, ms, "recusada")
        else:
            return PingResult(seq, False, ms, f"erro({err})")
    except socket.timeout:
        return PingResult(seq, False, 0.0, "timeout")
    except OSError as e:
        return PingResult(seq, False, 0.0, str(e))
    finally:
        sock.close()


# ---------------------------------------------------------------------------
# ICMP ping (uma tentativa)
# ---------------------------------------------------------------------------

def icmp_ping_once(ip: str, family: int, seq: int, pid: int,
                   timeout_ms: int = 2000,
                   length: Optional[int] = None,
                   dont_fragment: bool = False) -> PingResult:
    is_ipv6 = (family == socket.AF_INET6)
    proto = socket.IPPROTO_ICMPV6 if is_ipv6 else socket.IPPROTO_ICMP
    raw = socket.socket(family, socket.SOCK_RAW, proto)
    try:
        if dont_fragment:
            set_dont_fragment(raw, family)
        raw.settimeout(timeout_ms / 1000.0)
        pkt = _build_icmp_echo(seq, pid, is_ipv6, length)
        t0 = time.perf_counter()
        raw.sendto(pkt, (ip, 0))

        deadline = t0 + timeout_ms / 1000.0
        while time.perf_counter() < deadline:
            remaining = deadline - time.perf_counter()
            ready = select.select([raw], [], [], max(0, remaining))[0]
            if not ready:
                break
            data, addr = raw.recvfrom(4096)
            ms = (time.perf_counter() - t0) * 1000

            icmp_off = (data[0] & 0x0F) * 4 if not is_ipv6 else 0
            icmp = data[icmp_off:]
            if len(icmp) < 8:
                continue

            i_type = icmp[0]
            expected_reply = 129 if is_ipv6 else 0
            if i_type == expected_reply:
                r_pid = struct.unpack("!H", icmp[4:6])[0]
                r_seq = struct.unpack("!H", icmp[6:8])[0]
                if r_pid == (pid & 0xFFFF) and r_seq == (seq & 0xFFFF):
                    ttl = str(data[8]) if not is_ipv6 else "-"
                    return PingResult(seq, True, ms, f"ttl={ttl}")
            elif i_type in (3, 11):
                code = icmp[1]
                if i_type == 3 and code == 4:
                    return PingResult(seq, False, ms, "mtu exceeded")
                return PingResult(seq, False, ms, "unreachable")

        return PingResult(seq, False, 0.0, "timeout")
    except PermissionError:
        raise
    except socket.timeout:
        return PingResult(seq, False, 0.0, "timeout")
    except OSError as e:
        return PingResult(seq, False, 0.0, str(e))
    finally:
        raw.close()


# ---------------------------------------------------------------------------
# UDP ping (uma tentativa)
# ---------------------------------------------------------------------------

def _get_udp_payload(port: int, length: int) -> bytes:
    if length and length > 0:
        return b"A" * length
    if port == 53:
        return bytes.fromhex(
            "aaaa010000010000000000000667"
            "6f6f676c6503636f6d0000010001"
        )
    if port == 67:
        # DHCP Discover (mínimo válido: op=1, htype=1, hlen=6, magic cookie)
        pkt = bytearray(300)
        pkt[0] = 0x01   # op: BOOTREQUEST
        pkt[1] = 0x01   # htype: Ethernet
        pkt[2] = 0x06   # hlen
        pkt[3] = 0x00   # hops
        pkt[4:8] = b"\xde\xad\xbe\xef"  # xid
        pkt[236:240] = b"\x63\x82\x53\x63"  # magic cookie
        pkt[240] = 0x35; pkt[241] = 0x01; pkt[242] = 0x01  # DHCP Discover
        pkt[243] = 0xff  # end option
        return bytes(pkt)
    if port == 123:
        return b"\x1b" + b"\x00" * 47
    if port == 137:
        # NetBIOS Name Service — Node Status Request para "*"
        return bytes.fromhex(
            "a78f00000001000000000000"
            "20434b4141414141414141414141414141"
            "4141414141414141414141414141410000210001"
        )
    if port == 161:
        return bytes.fromhex(
            "302602010104067075626c6963"
            "a01902042171c7b8020100020100"
            "300b300906052b060102010500"
        )
    if port == 5353:
        # mDNS query para _services._dns-sd._udp.local (tipo PTR, classe IN)
        return (
            b"\x00\x00"              # transaction ID
            b"\x00\x00"              # flags: standard query
            b"\x00\x01"              # questions: 1
            b"\x00\x00\x00\x00\x00\x00"  # answers / authority / additional: 0
            b"\x09_services"
            b"\x07_dns-sd"
            b"\x04_udp"
            b"\x05local"
            b"\x00"                  # root label
            b"\x00\x0c"              # type PTR
            b"\x00\x01"              # class IN
        )
    return b"nocping-probe\r\n\r\n"


def udp_ping_once(ip: str, port: int, family: int, seq: int,
                  timeout_ms: int = 2000,
                  length: int = 0,
                  dont_fragment: bool = False) -> PingResult:
    is_ipv6 = (family == socket.AF_INET6)
    icmp_proto = socket.IPPROTO_ICMPV6 if is_ipv6 else socket.IPPROTO_ICMP
    icmp_sock = socket.socket(family, socket.SOCK_RAW, icmp_proto)
    icmp_sock.setblocking(False)
    udp = socket.socket(family, socket.SOCK_DGRAM)
    try:
        if dont_fragment:
            set_dont_fragment(udp, family)
        udp.setblocking(False)
        payload = _get_udp_payload(port, length)

        # Limpar buffer ICMP antes de enviar
        while select.select([icmp_sock], [], [], 0)[0]:
            try:
                icmp_sock.recvfrom(4096)
            except OSError:
                break

        t0 = time.perf_counter()
        try:
            udp.sendto(payload, (ip, port))
        except BlockingIOError:
            pass

        deadline = t0 + timeout_ms / 1000.0
        while time.perf_counter() < deadline:
            remaining = deadline - time.perf_counter()
            ready = select.select([icmp_sock, udp], [], [], max(0, remaining))[0]
            if not ready:
                break
            ms = (time.perf_counter() - t0) * 1000

            if icmp_sock in ready:
                data, _ = icmp_sock.recvfrom(4096)
                typ = _icmp_type(data, family)
                if not is_ipv6 and typ == 3:
                    code = data[((data[0] & 0xF) * 4) + 1]
                    if code == 4:
                        return PingResult(seq, False, ms, "fragmentation needed")
                    return PingResult(seq, True, ms, f"icmp type={typ}")
                elif is_ipv6 and typ == 2:
                    return PingResult(seq, False, ms, "fragmentation needed")
                return PingResult(seq, True, ms, f"icmp type={typ}")

            if udp in ready:
                try:
                    udp.recvfrom(4096)
                    ms = (time.perf_counter() - t0) * 1000
                    return PingResult(seq, True, ms, "udp response")
                except OSError:
                    pass

        return PingResult(seq, False, 0.0, "timeout")
    except PermissionError:
        raise
    except OSError as e:
        return PingResult(seq, False, 0.0, str(e))
    finally:
        udp.close()
        icmp_sock.close()


# ---------------------------------------------------------------------------
# Port Scan
# ---------------------------------------------------------------------------

def _parse_ports(spec: str) -> list:
    if not spec or not spec.strip():
        return list(range(1, 1025))
    ports = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            ports.extend(range(int(a), int(b) + 1))
        else:
            ports.append(int(part))
    return sorted(set(ports))


async def _scan_port_async(loop: asyncio.AbstractEventLoop,
                           ip: str, port: int, family: int,
                           timeout_s: float) -> tuple:
    t0 = time.perf_counter()
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.setblocking(False)
    try:
        await asyncio.wait_for(loop.sock_connect(sock, (ip, port)), timeout=timeout_s)
        ms = (time.perf_counter() - t0) * 1000
        return port, True, ms, "TCP"
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        ms = (time.perf_counter() - t0) * 1000
        return port, False, ms, "TCP"
    finally:
        try:
            sock.close()
        except OSError:
            pass


async def _scan_udp_port_async(loop: asyncio.AbstractEventLoop,
                                ip: str, port: int, family: int,
                                timeout_s: float) -> tuple:
    # run_in_executor: socket.settimeout + recv é confiável para UDP no Windows
    def _probe() -> tuple:
        t0 = time.perf_counter()
        sock = socket.socket(family, socket.SOCK_DGRAM)
        sock.settimeout(timeout_s)
        try:
            sock.connect((ip, port))
            sock.send(_get_udp_payload(port, 0))
            try:
                sock.recv(1024)
                return True, (time.perf_counter() - t0) * 1000
            except socket.timeout:
                return False, (time.perf_counter() - t0) * 1000
            except (ConnectionRefusedError, OSError):
                return False, (time.perf_counter() - t0) * 1000
        except OSError:
            return False, (time.perf_counter() - t0) * 1000
        finally:
            try:
                sock.close()
            except OSError:
                pass

    t0 = time.perf_counter()
    try:
        is_open, ms = await asyncio.wait_for(
            loop.run_in_executor(None, _probe),
            timeout=timeout_s + 1.0,
        )
    except asyncio.TimeoutError:
        is_open, ms = False, (time.perf_counter() - t0) * 1000
    return port, is_open, ms, "UDP"


async def _run_scan_async(ip: str, family: int, ports: list,
                          timeout_s: float,
                          on_result: Optional[Callable],
                          stop_event: Optional[threading.Event],
                          max_concurrent: int,
                          protocol: str) -> list:
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(max_concurrent)
    results = []

    async def scan_one(port: int, proto: str):
        if stop_event and stop_event.is_set():
            return
        async with sem:
            if stop_event and stop_event.is_set():
                return
            if proto == "UDP":
                result = await _scan_udp_port_async(loop, ip, port, family, timeout_s)
            else:
                result = await _scan_port_async(loop, ip, port, family, timeout_s)
        results.append(result)
        if on_result:
            on_result(*result)

    tasks = []
    if protocol in ("TCP", "TCP+UDP"):
        tasks += [scan_one(p, "TCP") for p in ports]
    if protocol in ("UDP", "TCP+UDP"):
        tasks += [scan_one(p, "UDP") for p in ports]

    await asyncio.gather(*tasks)
    return results


def scan_ports(ip: str, family: int, ports: list,
               timeout_ms: int = 200,
               on_result: Optional[Callable] = None,
               stop_event: Optional[threading.Event] = None,
               max_threads: int = 200,
               protocol: str = "TCP") -> list:
    """
    Varre portas usando asyncio (IOCP no Windows) para timeout confiável.
    Chama on_result(port, is_open, ms, protocol) para cada porta.
    """
    timeout_s = timeout_ms / 1000.0
    n_tasks = len(ports) * (2 if protocol == "TCP+UDP" else 1)
    max_concurrent = min(max_threads, n_tasks, 512)

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(
            _run_scan_async(ip, family, ports, timeout_s,
                            on_result, stop_event, max_concurrent, protocol)
        )
    finally:
        loop.close()

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Banner Grab + TLS
# ---------------------------------------------------------------------------

def banner_grab(ip: str, port: int, family: int,
                timeout_ms: int = 2000) -> dict:
    """
    Retorna dict com chaves:
      connected, rtt_ms, banner, tls_version, cipher, cn, expiry, error
    """
    result = {
        "connected": False, "rtt_ms": 0.0, "banner": "",
        "tls_version": None, "cipher": None, "cn": None,
        "expiry": None, "error": None,
    }
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout_ms / 1000.0)
        t0 = time.perf_counter()
        sock.connect((ip, port))
        result["rtt_ms"] = (time.perf_counter() - t0) * 1000
        result["connected"] = True

        # Tentar HTTP para banner
        try:
            sock.sendall(
                b"HEAD / HTTP/1.1\r\nHost: " +
                ip.encode() +
                b"\r\nConnection: close\r\n\r\n"
            )
            ready = select.select([sock], [], [], 2.0)[0]
            if ready:
                data = sock.recv(4096)
                result["banner"] = data.decode("utf-8", errors="replace").strip()
        except OSError:
            pass
    except socket.timeout:
        result["error"] = "timeout"
        return result
    except OSError as e:
        result["error"] = str(e)
        return result
    finally:
        sock.close()

    # Tentar TLS
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        tls_sock = ctx.wrap_socket(
            socket.socket(family, socket.SOCK_STREAM),
            server_hostname=ip,
        )
        tls_sock.settimeout(timeout_ms / 1000.0)
        tls_sock.connect((ip, port))
        cipher = tls_sock.cipher()
        cert = tls_sock.getpeercert()
        tls_sock.close()

        result["tls_version"] = cipher[1] if cipher else None
        result["cipher"] = cipher[0] if cipher else None
        if cert:
            for field in cert.get("subject", []):
                for k, v in (field if isinstance(field, list) else [field]):
                    if k == "commonName":
                        result["cn"] = v
            result["expiry"] = cert.get("notAfter")
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# Traceroute (ICMP TTL-based hop discovery)
# ---------------------------------------------------------------------------

def traceroute_hop(target_ip: str, family: int, ttl: int, seq: int, pid: int,
                   timeout_ms: int = 2000) -> dict:
    """
    Envia um pacote ICMP Echo com TTL fixo e aguarda resposta.
    Retorna dict: ttl, from_ip, elapsed_ms, timeout, destination_reached, error
    """
    is_ipv6 = (family == socket.AF_INET6)
    proto = socket.IPPROTO_ICMPV6 if is_ipv6 else socket.IPPROTO_ICMP
    raw = socket.socket(family, socket.SOCK_RAW, proto)
    result: dict = {
        "ttl": ttl, "from_ip": None, "elapsed_ms": 0.0,
        "timeout": False, "destination_reached": False, "error": None,
    }
    try:
        if is_ipv6:
            raw.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_UNICAST_HOPS, ttl)
        else:
            raw.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
        raw.settimeout(timeout_ms / 1000.0)
        pkt = _build_icmp_echo(seq, pid, is_ipv6, None)
        t0 = time.perf_counter()
        raw.sendto(pkt, (target_ip, 0))

        deadline = t0 + timeout_ms / 1000.0
        while time.perf_counter() < deadline:
            remaining = deadline - time.perf_counter()
            ready = select.select([raw], [], [], max(0.0, remaining))[0]
            if not ready:
                break
            data, addr = raw.recvfrom(4096)
            ms = (time.perf_counter() - t0) * 1000
            icmp_off = (data[0] & 0x0F) * 4 if not is_ipv6 else 0
            icmp = data[icmp_off:]
            if len(icmp) < 8:
                continue
            i_type = icmp[0]
            from_ip = addr[0]
            time_exceeded = 3 if is_ipv6 else 11
            if i_type == time_exceeded:  # Time Exceeded (ICMPv4=11, ICMPv6=3)
                result["from_ip"] = from_ip
                result["elapsed_ms"] = ms
                return result
            expected_reply = 129 if is_ipv6 else 0
            if i_type == expected_reply:
                r_pid = struct.unpack("!H", icmp[4:6])[0]
                r_seq = struct.unpack("!H", icmp[6:8])[0]
                if r_pid == (pid & 0xFFFF) and r_seq == (seq & 0xFFFF):
                    result["from_ip"] = from_ip
                    result["elapsed_ms"] = ms
                    result["destination_reached"] = True
                    return result
        result["timeout"] = True
    except PermissionError:
        result["error"] = "permission"
    except OSError as e:
        result["error"] = str(e)
    finally:
        raw.close()
    return result


# ---------------------------------------------------------------------------
# Cálculo de estatísticas
# ---------------------------------------------------------------------------

def calc_stats(results: list) -> dict:
    ok = [r for r in results if r.success and r.elapsed_ms > 0]
    total = len(results)
    lost = total - len(ok)
    times = [r.elapsed_ms for r in ok]
    return {
        "total": total,
        "received": len(ok),
        "lost": lost,
        "loss_pct": (lost / total * 100) if total else 0.0,
        "min_ms": min(times) if times else 0.0,
        "avg_ms": statistics.mean(times) if times else 0.0,
        "max_ms": max(times) if times else 0.0,
        "jitter_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
    }
