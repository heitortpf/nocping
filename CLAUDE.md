# NOCPing — Contexto do Projeto

Ferramenta de diagnóstico de rede para analistas NOC, escrita em Python + PyQt6.
Desenvolvida e mantida neste repositório em `C:\Users\Livre\nocping`.

## Como rodar

```
python main.py
```

Dependências: `PyQt6`, `darkdetect`  
Python: 3.14 (Windows 11)  
ICMP e UDP (modo monitor/ping) requerem execução como Administrador.  
Port Scan TCP/UDP **não** requer admin.

---

## Estrutura de arquivos

```
main.py                  — entry point
core/
  models.py              — dataclasses e enums (PingResult, ProbeConfig, ProbeMode, IPVersion, HostStatus)
  network.py             — funções de rede puras (sem GUI)
  workers.py             — QThread workers que chamam network.py e emitem sinais PyQt6
ui/
  main_window.py         — janela principal, sistema de temas, multi-janela
  monitor_tab.py         — aba de monitoramento multi-host estilo vmPing
  scan_tab.py            — aba de port scan TCP/UDP
  banner_tab.py          — aba de banner grab + inspeção TLS/SSL
  traceroute_tab.py      — aba de traceroute ICMP
  widgets/
    host_card.py         — card individual de host no monitor
    rtt_graph.py         — gráfico de RTT em tempo real
```

---

## Sistema de temas (ui/main_window.py)

- Autodetect via `darkdetect.isDark()`; fallback por luminosidade do QPalette
- `DARK_PALETTE` e `LIGHT_PALETTE`: dicts `QPalette.ColorRole → hex`
- `apply_theme(app, dark)` — define palette + stylesheet global
- `_build_stylesheet(dark)` — gera CSS dinâmico com f-string; inclui setas do QSpinBox como PNGs gerados em runtime via QPainter, salvos em tempdir e cacheados em `_arrow_cache`
- **Regra importante:** todos os widgets das abas usam `palette()` no stylesheet (ex: `palette(base)`, `palette(button)`) para que o tema seja aplicado automaticamente. Nunca usar cores hex hardcoded em backgrounds/bordas de painéis ou tabelas.

### Multi-janela
- `MainWindow._instances: list["MainWindow"]` — lista de classe com todas as janelas abertas
- `Ctrl+N` abre nova janela herdando o tema da janela atual
- `_toggle_theme()` itera `_instances` e aplica o tema em todas

---

## Port Scan (core/network.py + ui/scan_tab.py)

### Problema histórico resolvido
TCP com `settimeout()` no Windows ignora o timeout para portas bloqueadas por firewall (o stack TCP faz retransmissão por ~21s). A solução foi usar asyncio:
- TCP: `asyncio.wait_for(loop.sock_connect(...))` — usa IOCP no Windows, timeout confiável
- UDP: `loop.run_in_executor(None, _probe)` com `socket.settimeout()` — recv UDP respeita timeout corretamente no Windows; `loop.sock_recv` no ProactorEventLoop (IOCP) não funciona de forma confiável para sockets UDP criados manualmente

### Fluxo do scan
```
ScanTab._start()
  → ScanWorker(host, port_spec, ip_version, timeout_ms, max_threads, protocol)
      → resolve_host()
      → _parse_ports(port_spec)
      → scan_ports(ip, family, ports, ..., protocol=)
          → asyncio.new_event_loop()
          → _run_scan_async(...)  [semaphore controla concorrência]
              → _scan_port_async()     [TCP]
              → _scan_udp_port_async() [UDP via executor]
          → on_result(port, is_open, ms, proto) → ScanWorker.port_result.emit(...)
  → ScanTab._on_port_result(port, is_open, ms, protocol)  [só mostra is_open=True]
```

### Protocolo
- Combo na UI: TCP / UDP / TCP+UDP
- Em TCP+UDP o total de portas é `n_ports × 2` (barra de progresso reflete isso)
- `port_result` signal: `pyqtSignal(int, bool, float, str)` — porta, aberta, ms, protocolo

### Presets de portas
`_PRESETS` em scan_tab.py:
- Personalizado (campo livre)
- Top 20 — rápido
- Top 100 — comum
- Todas (1-65535)

### Probes UDP específicos (core/network.py `_get_udp_payload`)
- Porta 53 → query DNS real para google.com
- Porta 123 → pacote NTP
- Porta 161 → SNMP GetRequest
- Outras → payload genérico `b"nocping-probe\r\n\r\n"`

UDP só reporta portas que **respondem** ao probe. Portas silenciosas (timeout) e fechadas (ICMP unreachable = ConnectionRefusedError) são descartadas.

### Cleanup de worker (evitar bug de scan duplo)
`_cleanup_worker()` em ScanTab: desconecta sinais, para o worker, chama `wait(2000)` e `deleteLater()` antes de criar um novo. Isso previne que sinais do worker anterior disparem no contexto do scan novo.

---

## Monitor de hosts (ui/monitor_tab.py + ui/widgets/host_card.py)

- Adiciona `HostCard` por host; cada card tem seu `PingWorker`
- Layout de cards: `_FlowLayout` customizado (quebra linha automaticamente)
- Modos: TCP, ICMP, UDP (ICMP e UDP requerem admin)
- Status bar da janela mostra contadores: Hosts / Up / Down

---

## Traceroute (ui/traceroute_tab.py)

- Requer admin (raw socket ICMP)
- `TracerouteWorker` envia ICMP com TTL crescente
- Tabela: Hop, IP, Hostname, RTT, Notas

---

## Banner Grab / TLS (ui/banner_tab.py)

- Conecta TCP, envia `HEAD /` HTTP, lê banner
- Tenta wrap TLS para extrair: versão, cifra, CN do certificado, validade

---

## Layouts e alinhamento

- Painéis de controle (Monitor, Traceroute) usam `QGridLayout` com linha 0 = rótulos e linha 1 = campos, `columnStretch(0, 1)` para o campo host ser expansível
- Port Scan usa duas linhas (`row1`, `row2`) em `QHBoxLayout` para ser responsivo em janelas estreitas
- Cor de rótulos: `color:#9ca3af` (estilo fixo, não palette — é decorativo)

---

## Pendências / ideias para próximas sessões

- Adicionar mais probes UDP (ex: porta 67 DHCP, 137 NetBIOS, 5353 mDNS)
- Opção de mostrar portas UDP "open|filtered" (timeout sem ICMP unreachable) — atualmente só "open" é mostrado
- Exportar resultados do Monitor para CSV/JSON
- Histórico de RTT por host no Monitor
- Salvar configuração de hosts monitorados entre sessões
- Ícone da aplicação (.ico)
- Empacotamento com PyInstaller
