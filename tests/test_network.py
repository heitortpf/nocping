import struct
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.network import (
    _parse_ports, _build_icmp_echo, _checksum, is_admin,
    _get_udp_payload, calc_stats,
)
from core.models import PingResult


# ---------------------------------------------------------------------------
# _parse_ports
# ---------------------------------------------------------------------------

def test_parse_ports_range():
    assert _parse_ports("1-5") == [1, 2, 3, 4, 5]


def test_parse_ports_list():
    assert _parse_ports("22,80,443") == [22, 80, 443]


def test_parse_ports_mixed():
    assert _parse_ports("22,80-82,443") == [22, 80, 81, 82, 443]


def test_parse_ports_empty():
    assert _parse_ports("") == list(range(1, 1025))


def test_parse_ports_whitespace():
    assert _parse_ports("  ") == list(range(1, 1025))


def test_parse_ports_dedup_and_sort():
    result = _parse_ports("443,80,80,22")
    assert result == sorted(set([443, 80, 80, 22]))


# ---------------------------------------------------------------------------
# _build_icmp_echo
# ---------------------------------------------------------------------------

def test_icmp_echo_ipv4_type():
    pkt = _build_icmp_echo(seq=1, pid=1000, is_ipv6=False)
    assert pkt[0] == 8  # type ECHO REQUEST


def test_icmp_echo_ipv6_type():
    pkt = _build_icmp_echo(seq=1, pid=1000, is_ipv6=True)
    assert pkt[0] == 128  # type ECHO REQUEST IPv6


def test_icmp_echo_checksum_valid():
    pkt = _build_icmp_echo(seq=1, pid=1000, is_ipv6=False)
    # Recomputar checksum sobre o pacote; deve resultar em 0
    assert _checksum(pkt) == 0


def test_icmp_echo_seq_encoded():
    pkt = _build_icmp_echo(seq=42, pid=1000, is_ipv6=False)
    seq_in_pkt = struct.unpack("!H", pkt[6:8])[0]
    assert seq_in_pkt == 42


def test_icmp_echo_pid_encoded():
    pkt = _build_icmp_echo(seq=1, pid=12345, is_ipv6=False)
    pid_in_pkt = struct.unpack("!H", pkt[4:6])[0]
    assert pid_in_pkt == 12345


def test_icmp_echo_custom_length():
    pkt = _build_icmp_echo(seq=1, pid=1000, is_ipv6=False, length=32)
    # header = 8 bytes, payload = 32 bytes
    assert len(pkt) == 8 + 32


# ---------------------------------------------------------------------------
# PingResult
# ---------------------------------------------------------------------------

def test_ping_result_defaults():
    r = PingResult(seq=1, success=True)
    assert r.elapsed_ms == 0.0
    assert r.note == ""


def test_ping_result_timeout():
    r = PingResult(seq=1, success=False, elapsed_ms=0.0, note="timeout")
    assert r.success is False
    assert r.note == "timeout"


def test_ping_result_success_with_rtt():
    r = PingResult(seq=5, success=True, elapsed_ms=24.5)
    assert r.seq == 5
    assert r.elapsed_ms == 24.5


# ---------------------------------------------------------------------------
# is_admin
# ---------------------------------------------------------------------------

def test_is_admin_returns_bool():
    result = is_admin()
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Testes live (requerem rede) — marcados para pular em CI
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_resolve_localhost():
    from core.network import resolve_host
    from core.models import IPVersion
    family, ip = resolve_host("localhost", 80, IPVersion.AUTO)
    assert ip in ("127.0.0.1", "::1")


@pytest.mark.live
def test_tcp_ping_open_port():
    """Testa contra o próprio localhost — precisa de algo ouvindo."""
    import socket as _socket
    # Abre servidor temporário para o teste
    srv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    srv.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        from core.network import tcp_ping_once
        result = tcp_ping_once("127.0.0.1", port, _socket.AF_INET, timeout_ms=1000)
        assert result.success is True
        assert result.elapsed_ms > 0
    finally:
        srv.close()


@pytest.mark.live
def test_tcp_ping_closed_port():
    from core.network import tcp_ping_once, resolve_host
    from core.models import IPVersion
    import socket as _socket
    family, ip = resolve_host("127.0.0.1", 1, IPVersion.IPV4)
    result = tcp_ping_once(ip, 1, family, timeout_ms=500)
    # Porta fechada: sucesso=True (recusada) ou False (timeout) — não deve lançar exceção
    assert isinstance(result.success, bool)


# ---------------------------------------------------------------------------
# _build_icmp_echo — payload após renomear "rtech-data" → "nocping"
# ---------------------------------------------------------------------------

def test_icmp_payload_uses_nocping_prefix():
    pkt = _build_icmp_echo(seq=1, pid=1, is_ipv6=False)
    assert pkt[8:15] == b"nocping", "payload deve começar com b'nocping'"

def test_icmp_payload_not_rtech():
    pkt = _build_icmp_echo(seq=1, pid=1, is_ipv6=False)
    assert b"rtech" not in pkt

def test_icmp_default_payload_total_length():
    # header 8 bytes + "nocping"(7) + bytes(range(25))(25) = 40 bytes
    pkt = _build_icmp_echo(seq=1, pid=1, is_ipv6=False)
    assert len(pkt) == 40


# ---------------------------------------------------------------------------
# calc_stats
# ---------------------------------------------------------------------------

def _make_results(*pairs):
    return [PingResult(seq=i + 1, success=s, elapsed_ms=ms)
            for i, (s, ms) in enumerate(pairs)]

def test_calc_stats_all_success():
    s = calc_stats(_make_results((True, 10.0), (True, 20.0), (True, 30.0)))
    assert s["total"] == 3
    assert s["received"] == 3
    assert s["loss_pct"] == pytest.approx(0.0)
    assert s["avg_ms"] == pytest.approx(20.0)
    assert s["min_ms"] == pytest.approx(10.0)
    assert s["max_ms"] == pytest.approx(30.0)

def test_calc_stats_all_lost():
    s = calc_stats(_make_results((False, 0.0), (False, 0.0)))
    assert s["received"] == 0
    assert s["loss_pct"] == pytest.approx(100.0)
    assert s["avg_ms"] == pytest.approx(0.0)

def test_calc_stats_partial_loss():
    s = calc_stats(_make_results((True, 10.0), (False, 0.0),
                                 (True, 30.0), (False, 0.0)))
    assert s["loss_pct"] == pytest.approx(50.0)
    assert s["min_ms"] == pytest.approx(10.0)
    assert s["max_ms"] == pytest.approx(30.0)

def test_calc_stats_empty():
    s = calc_stats([])
    assert s["total"] == 0
    assert s["received"] == 0
    assert s["loss_pct"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _parse_ports — edge cases
# ---------------------------------------------------------------------------

def test_parse_ports_single():
    assert _parse_ports("443") == [443]

def test_parse_ports_reversed_range_is_empty_or_safe():
    result = _parse_ports("100-99")
    assert isinstance(result, list)

def test_parse_ports_accepts_any_int_no_range_validation():
    # _parse_ports não valida limites TCP — aceita qualquer inteiro; cabe ao caller filtrar
    result = _parse_ports("80,65535")
    assert 80 in result and 65535 in result


# ---------------------------------------------------------------------------
# _get_udp_payload
# ---------------------------------------------------------------------------

def test_udp_payload_dns_contains_google():
    payload = _get_udp_payload(53, 0)
    assert b"google" in payload

def test_udp_payload_dns_min_length():
    payload = _get_udp_payload(53, 0)
    assert len(payload) >= 12

def test_udp_payload_ntp_is_48_bytes():
    payload = _get_udp_payload(123, 0)
    assert len(payload) == 48

def test_udp_payload_generic_contains_nocping():
    payload = _get_udp_payload(9999, 0)
    assert b"nocping" in payload

def test_udp_payload_differs_between_protocols():
    assert _get_udp_payload(53, 0) != _get_udp_payload(123, 0)
    assert _get_udp_payload(123, 0) != _get_udp_payload(161, 0)

def test_udp_payload_custom_length():
    payload = _get_udp_payload(9999, 32)
    assert payload == b"A" * 32

def test_udp_payload_dhcp_magic_cookie():
    payload = _get_udp_payload(67, 0)
    assert len(payload) == 300
    assert payload[0] == 0x01                          # BOOTREQUEST
    assert payload[236:240] == b"\x63\x82\x53\x63"    # magic cookie
    assert payload[242] == 0x01                        # DHCP Discover option

def test_udp_payload_netbios_length():
    payload = _get_udp_payload(137, 0)
    assert len(payload) >= 12
    assert payload[4] == 0x00 and payload[5] == 0x01   # QDCOUNT = 1

def test_udp_payload_mdns_ptr_query():
    payload = _get_udp_payload(5353, 0)
    assert b"_services" in payload
    assert b"_dns-sd" in payload
    assert b"local" in payload
    assert payload[4:6] == b"\x00\x01"                 # QDCOUNT = 1
