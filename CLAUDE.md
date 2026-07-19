# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# AG Kit — Protocolo de Agentes e Skills

Este projeto usa o **AG Kit** (Antigravity Kit). Antes de qualquer implementação, siga o protocolo abaixo.

## Protocolo de Agentes

Quando o usuário mencionar `@agent-name` ou quando a tarefa se encaixar no domínio de um agente, **leia o arquivo do agente antes de responder**:

```
.agent/agents/<nome-do-agente>.md
```

Agentes disponíveis: `frontend-specialist`, `backend-specialist`, `database-architect`, `mobile-developer`, `game-developer`, `devops-engineer`, `security-auditor`, `penetration-tester`, `test-engineer`, `debugger`, `performance-optimizer`, `seo-specialist`, `documentation-writer`, `product-manager`, `product-owner`, `project-planner`, `qa-automation-engineer`, `code-archaeologist`, `explorer-agent`, `orchestrator`

### Seleção automática de agente

Analise silenciosamente o domínio do pedido e aplique o agente mais adequado. Informe ao usuário qual agente está sendo usado:

```
🤖 Aplicando conhecimento de `@[nome-do-agente]`...
```

### Skills

Após selecionar o agente, verifique o campo `skills:` no frontmatter do arquivo `.md` do agente e leia os arquivos relevantes em `.agent/skills/<skill>/SKILL.md`.

## Workflows (Slash Commands)

| Comando | Descrição |
|---------|-----------|
| `/brainstorm` | Descoberta socrática |
| `/coordinate` | Coordenação multi-agente |
| `/create` | Criar nova feature |
| `/debug` | Depurar problemas |
| `/deploy` | Deploy da aplicação |
| `/enhance` | Melhorar código existente |
| `/orchestrate` | Coordenação multi-agente |
| `/plan` | Quebrar tarefa em etapas |
| `/preview` | Preview de mudanças |
| `/remember` | Salvar em memória persistente |
| `/status` | Verificar status do projeto |
| `/test` | Rodar testes |
| `/ui-ux-pro-max` | Design com 50 estilos |
| `/verify` | Provar que o código funciona rodando |

---

# NOCPing — Contexto do Projeto

Ferramenta de diagnóstico de rede para analistas NOC, escrita em Python + PyQt6.
Desenvolvida e mantida neste repositório em `C:\NOCPing`.

## Como rodar

```
python main.py
```

Dependências: `PyQt6`, `pyqtgraph`, `darkdetect`
Python: 3.14 (Windows 11)
ICMP e UDP (modo monitor/ping) requerem execução como Administrador.
Port Scan TCP/UDP **não** requer admin.

---

## Estrutura de arquivos

```
main.py                  — entry point (carrega NOCPing.ico via QIcon)
take_shots.py            — captura automática de screenshots das 5 abas via win32gui + PIL
docs/
  PLAN-features.md       — plano de features executado na v1.1.0
  PLAN.md                — plano em aberto (proposta de status WARNING para perda de pacote isolada, ver seção Pendências)
core/
  models.py              — dataclasses e enums (PingResult, ProbeConfig, ProbeMode, IPVersion, HostStatus)
  network.py             — funções de rede puras (sem GUI)
  workers.py             — QThread workers que chamam network.py e emitem sinais PyQt6
  config_store.py        — persistência da lista de hosts monitorados (nocping_hosts.json)
  history_store.py       — singleton SQLite thread-safe (fila assíncrona) para histórico de RTT por host
ui/
  main_window.py         — janela principal, temas, multi-janela, screenshot, bandeja
  quick_ping_tab.py      — aba inicial: ping rápido de host único (TCP/ICMP/UDP), gráfico RTT expandido, console de log
  monitor_tab.py         — aba de monitoramento multi-host estilo vmPing
  scan_tab.py            — aba de port scan TCP/UDP
  banner_tab.py          — aba de banner grab + inspeção TLS/SSL
  traceroute_tab.py      — aba de traceroute ICMP
  mtr_tab.py             — aba MTR (My TraceRoute) com estatísticas contínuas por hop
  widgets/
    host_card.py         — card individual de host no monitor
    rtt_graph.py         — gráfico de RTT em tempo real
    history_dialog.py    — diálogo de histórico RTT (gráfico + tabela + export CSV)
    _utils.py            — helpers e estilos compartilhados (rtt_color, field_label, PRIMARY_BTN_STYLE, TABLE_STYLE)
tests/
  test_network.py        — testes de core/network.py (38 testes, CI-safe)
  test_config_store.py   — testes de core/config_store.py
  test_history_store.py  — testes de core/history_store.py (9 testes, thread-safety)
  test_rtt_utils.py      — testes de ui/widgets/_utils.py
  test_workers.py        — testes de PingWorker e ScanWorker com mocks
screenshots/
  monitor.png / portscan.png / banner.png / traceroute.png / mtr.png
NOCPing.ico              — ícone da aplicação
```

---

## Sistema de temas (ui/main_window.py)

- Autodetect via `darkdetect.isDark()`; fallback por luminosidade do QPalette
- `DARK_PALETTE` e `LIGHT_PALETTE`: dicts `QPalette.ColorRole → hex`
- `apply_theme(app, dark)` — define palette + stylesheet global
- `_build_stylesheet(dark)` — gera CSS dinâmico com f-string; inclui setas do QSpinBox como PNGs gerados em runtime via QPainter, salvos em tempdir e cacheados em `_arrow_cache`
- `_toggle_theme()` itera `_instances` e aplica o tema em todas as janelas abertas; também chama `card._graph.apply_theme(dark)` em todos os cards do monitor
- **Regra importante:** todos os widgets das abas usam `palette()` no stylesheet (ex: `palette(base)`, `palette(button)`) para que o tema seja aplicado automaticamente. Nunca usar cores hex hardcoded em backgrounds/bordas de painéis ou tabelas.

### Multi-janela
- `MainWindow._instances: list["MainWindow"]` — lista de classe com todas as janelas abertas
- `Ctrl+N` abre nova janela herdando o tema da janela atual
- `_toggle_theme()` itera `_instances` e aplica o tema em todas

### Screenshot integrado
`Arquivo → Salvar Screenshot...` (atalho `Ctrl+P`) usa `QScreen.grabWindow(self.winId())`.
Necessário porque o NOCPing roda como Administrador e o UIPI do Windows impede ferramentas de captura de menor privilégio (Snipping Tool, PrintScreen) de capturar a janela. A captura interna roda no mesmo processo, contorna o problema sem sacrificar desempenho.

### Bandeja do sistema (QSystemTrayIcon)
- `_build_tray()` cria `QSystemTrayIcon` com o ícone da app; menu: "Abrir NOCPing" / "Sair"
- Duplo-clique na bandeja → `_show_from_tray()` restaura a janela
- `_on_host_status_changed(host, old, new)` — emite `showMessage()` quando host vai DOWN ou volta UP
- Notificações ativáveis/desativáveis em `Visualizar → Notificações de host` (checkable QAction)
- Preferência persiste via `QSettings("NOCPing", "NOCPing")`, chave `notifications_enabled`
- Sinal que dispara as notificações: `MonitorTab.host_status_changed(host, old, new)` → conectado em `_build_tabs()`; originado em `HostCard.status_changed` emitido no `_set_status()` quando o status muda para UP/DOWN/ERROR

### closeEvent / _shutdown
`closeEvent` fecha a aplicação completamente, encerrando o processo. O ícone da bandeja é destruído automaticamente.

`QApplication.aboutToQuit` está conectado a `_shutdown()`, que encerra todos os workers:
```python
self._quick_ping.cleanup()
for card in self._monitor._cards: card.stop()
if self._scan: self._scan._cleanup_worker()
if self._banner: self._banner._cleanup_worker()
# TracerouteWorker e MTRWorker: stop() + wait(500)
```
As abas Scan/Banner/Traceroute/MTR são lazy-inicializadas (só no primeiro clique) — por isso os `if self._scan`/`if self._banner` antes de limpar: podem ser `None` se a aba nunca foi aberta.

---

## Quick Ping (ui/quick_ping_tab.py)

Aba inicial da aplicação (desde v1.3.0) — diagnóstico ágil de um único host, independente do Monitor.

- Suporta TCP/ICMP/UDP; gráfico RTT expandido + console de log estilo terminal (auto-scroll e cópia)
- Stats em tempo real: RTT atual, média, jitter, mínimo, máximo, perda
- Ao iniciar um novo ping (mudar IP/host), o worker anterior é parado automaticamente e o console é limpo antes do novo teste começar — evita a race condition do botão "Parar" (corrigida na v1.3.0)
- Usa `threading.get_ident() & 0xFFFF` como PID ICMP único da thread — ver seção **ICMP: PID por thread e Deep Packet Inspection** abaixo, pois esta aba compartilha `icmp_ping_once()` com o Monitor e pode sofrer cross-talk se essa regra for quebrada

---

## Módulo compartilhado (ui/widgets/_utils.py)

Centraliza helpers duplicados — importar sempre daqui:

```python
from .widgets._utils import rtt_color, field_label, PRIMARY_BTN_STYLE, TABLE_STYLE
```

- `rtt_color(ms)` — `#4ade80` (<50ms), `#facc15` (50-149ms), `#f87171` (≥150ms ou ≤0)
- `field_label(text)` — QLabel estilizado para rótulos de campos
- `PRIMARY_BTN_STYLE` — stylesheet padrão para botões de ação (roxo `#7c3aed`)
- `TABLE_STYLE` — stylesheet padrão para QTableWidget usando `palette()`

---

## Port Scan (core/network.py + ui/scan_tab.py)

### Problema histórico resolvido
TCP com `settimeout()` no Windows ignora o timeout para portas bloqueadas por firewall (o stack TCP faz retransmissão por ~21s). A solução foi usar asyncio:
- TCP: `asyncio.wait_for(loop.sock_connect(...))` — usa IOCP no Windows, timeout confiável
- UDP: `loop.run_in_executor(None, _probe)` com `socket.settimeout()` — recv UDP respeita timeout corretamente no Windows

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
  → ScanTab._on_port_result(port, is_open, ms, protocol)
```

### Protocolo
- Combo na UI: TCP / UDP / TCP+UDP
- Em TCP+UDP o total de portas é `n_ports × 2` (barra de progresso reflete isso)
- `port_result` signal: `pyqtSignal(int, bool, float, str)` — porta, aberta, ms, protocolo
- Checkbox "UDP open|filtered": exibe portas UDP sem resposta em amarelo (`◎ open|filtered`)

### Presets de portas
`_PRESETS` em scan_tab.py: Personalizado / Top 20 / Top 100 / Todas (1-65535)

### Probes UDP específicos (core/network.py `_get_udp_payload`)
- Porta 53 → query DNS real para google.com
- Porta 67 → DHCP Discover (300 bytes, magic cookie `\x63\x82\x53\x63`)
- Porta 123 → pacote NTP (48 bytes)
- Porta 137 → NetBIOS Name Service node status request
- Porta 161 → SNMP GetRequest
- Porta 5353 → mDNS PTR query para `_services._dns-sd._udp.local`
- Outras → payload genérico `b"nocping-probe\r\n\r\n"`

### Cleanup de worker
`_cleanup_worker()` em ScanTab e BannerTab: desconecta sinais, para o worker, chama `wait(2000)` e `deleteLater()`. Padrão obrigatório para evitar sinais duplicados.

---

## Monitor de hosts (ui/monitor_tab.py + ui/widgets/host_card.py)

- Adiciona `HostCard` por host; cada card tem seu `PingWorker`
- Layout de cards: `_FlowLayout` customizado (quebra linha automaticamente)
- Modos: TCP, ICMP, UDP (ICMP e UDP requerem admin)
- Status bar da janela mostra contadores: Hosts / Up / Down
- **Persistência de sessão:** `save_hosts(cards)` e `load_hosts()` via `core/config_store.py` — salva em `nocping_hosts.json` (ignorado pelo git)
- **Exportação:** botões CSV e JSON na action_row exportam stats de todos os hosts
- **Exportar RTT por host:** botão "⬇ Exportar RTT" em cada HostCard salva `_results` em CSV
- **Histórico de RTT:** cada `PingResult` é gravado em SQLite via `HistoryStore.instance().record()` em `_on_result`; botão "⏱ Histórico" abre `HistoryDialog`
- **Notificações:** `HostCard` emite `status_changed(host, old, new)` ao mudar para UP/DOWN/ERROR; `MonitorTab` repassa via `host_status_changed`

### PingWorker (core/workers.py)
Usa `threading.Event.wait(timeout)` no intervalo entre pings — para imediatamente ao chamar `stop()`, sem busy-wait. Para em < 200ms mesmo com `interval_ms=5000`.

---

## Traceroute (ui/traceroute_tab.py)

- Requer admin (raw socket ICMP)
- `TracerouteWorker` envia ICMP com TTL crescente
- DNS reverso por hop com timeout de 2s (thread daemon + `join(timeout=2.0)`) — não trava
- Tabela: Hop, IP, Hostname, RTT, Notas

---

## MTR — My TraceRoute (ui/mtr_tab.py + core/workers.py)

- Requer admin (raw socket ICMP)
- Traceroute **contínuo**: reenvia sondas indefinidamente e acumula estatísticas por hop
- `MTRWorker` (core/workers.py): itera TTL 1…N em loop; ao atingir o destino, fixa `current_max = ttl` e continua apenas até aquele hop
- DNS reverso por hop na primeira descoberta (thread daemon + `join(timeout=2.0)`)
- Sinais:
  - `hop_discovered(ttl, ip, hostname)` — primeiro avistamento de um hop
  - `hop_update(ttl, stats_dict)` — atualização de estatísticas a cada sonda
  - `error(str)` / `finished()`
- `stats_dict` contém: `loss_pct`, `sent`, `last_ms`, `avg_ms`, `best_ms`, `worst_ms`, `stdev_ms`
- Tabela: Hop / IP / Hostname / Loss% / Sent / Last / Avg / Best / Worst / StDev
- Coluna Hostname usa `ResizeMode.Stretch`; demais são `Fixed`
- `_loss_color(pct)` — `#4ade80` (0%), `#a3e635` (<5%), `#facc15` (<20%), `#f87171` (≥20%)
- Intervalo entre sondas: `_stop.wait(interval_ms / 1000.0)` — para imediatamente ao chamar `stop()`
- Parâmetros: host, ip_version, max_hops (1-64, default 30), timeout_ms (500-10000, default 1000), interval_ms (100-5000, default 200)

---

## Histórico de RTT (core/history_store.py + ui/widgets/history_dialog.py)

- `HistoryStore` é singleton thread-safe (`check_same_thread=False`, modo WAL)
- **Escrita assíncrona (v1.4.0):** `record()` apenas enfileira (`queue.Queue`) e retorna em O(1), sem bloquear a thread do worker; uma thread daemon dedicada (`_db_worker`) drena a fila em lotes de até `_BATCH_SIZE=50` e faz `executemany()` + `commit()` único por lote — isso eliminou o stuttering de UI causado por contenção no `_rw_lock` quando dezenas de hosts gravavam RTT simultaneamente
- `flush()` (`queue.join()`) força esperar a fila esvaziar antes de ler — usado internamente por `query()`/`clear()`/`hosts()` para garantir leitura consistente
- Banco em `nocping_history.db` na raiz do projeto (ignorado pelo git)
- Schema: tabela `rtt_history(id, host, ts, success, elapsed, note)` + índice `(host, ts)`
- Métodos: `record(host, result)`, `query(host, last_n) → list[dict]`, `clear(host)`, `hosts()`
- `query()` retorna ordem cronológica (mais antigo primeiro), limitado por `last_n`
- `HistoryDialog` — `QDialog` com gráfico pyqtgraph + tabela + seletor de limite (100/500/1000/tudo) + exportar CSV + limpar histórico com confirmação
- Acesso: botão "⏱ Histórico" em cada `HostCard` → `HistoryDialog(host).exec()`

---

## Banner Grab / TLS (ui/banner_tab.py)

- Conecta TCP, envia `HEAD /` HTTP, lê banner
- Tenta wrap TLS para extrair: versão, cifra, CN do certificado, validade
- `_cleanup_worker()` implementado — evita leak de sinais em cliques rápidos

---

## RTT Graph (ui/widgets/rtt_graph.py)

- `apply_theme(dark: bool)` — atualiza background e cor dos eixos
- `_apply_colors(dark)` — `#1e1e2e`/`#e6e9ef` de fundo; eixo cinza adaptativo
- Cor da curva via `rtt_color(avg)` de `_utils`
- **Throttling de renderização (v1.4.0):** `_redraw_timer` (QTimer, 100ms) limita o redesenho a no máximo 10 FPS; novos pontos só marcam `_needs_redraw = True` e o redesenho real (`_throttled_redraw`) só ocorre se o widget estiver visível (`self.isVisible()`) — abas/gráficos ocultos consomem 0% CPU mesmo recebendo dados

---

## Payload ICMP (core/network.py)

```python
payload = b"nocping" + bytes(range(25)) if length is None else b"A" * length
# Total: 8 bytes header + 7 (b"nocping") + 25 = 40 bytes
```

---

## ICMP: PID por thread e Deep Packet Inspection (core/network.py + core/workers.py)

### Problema histórico resolvido
Um socket ICMP raw recebe **todas** as respostas ICMP do sistema, não só as do processo. Com Quick Ping, Monitor e MTR rodando ao mesmo tempo (cada um em sua própria `QThread`), uma resposta destinada a uma aba podia ser lida por outra, causando perda de pacote reportada indevidamente e cross-talk de RTT entre abas.

### Solução
- Cada thread que envia ICMP (`PingWorker`, `TracerouteWorker`, `MTRWorker`) gera seu próprio identificador com `pid = threading.get_ident() & 0xFFFF` — nunca reutilizar um PID fixo ou compartilhado entre workers.
- `icmp_ping_once()` e `traceroute_hop()` (`core/network.py`) fazem **Deep Packet Inspection**: para pacotes Echo Reply, o `pid`/`seq` do cabeçalho ICMP são comparados diretamente; para erros ICMP (Time Exceeded, Destination Unreachable), o `pid`/`seq` originais são extraídos do payload interno (pacote IP+ICMP encapsulado no corpo do erro) e comparados — um pacote só é aceito se `pid` **e** `seq` baterem com o que foi enviado por aquela thread.
- Ao adicionar qualquer novo caminho que envie ICMP, sempre gerar o PID via `threading.get_ident()` dentro da própria thread e sempre filtrar respostas por `pid`+`seq` antes de aceitá-las — do contrário reintroduz o bug de cross-talk entre abas.

---

## Layouts e alinhamento

- Painéis de controle (Monitor, Traceroute) usam `QGridLayout` com linha 0 = rótulos e linha 1 = campos
- Port Scan usa duas linhas (`row1`, `row2`) em `QHBoxLayout` para ser responsivo
- Cor de rótulos: `color:#9ca3af` (estilo fixo, decorativo — não usar palette aqui)

---

## Testes automatizados

```bash
pytest tests/ -v -m "not live"   # CI-safe (77 testes)
pytest tests/ -v                  # completo (requer rede/admin)
```

- `test_network.py` — `_parse_ports`, `_build_icmp_echo`, `calc_stats`, `_get_udp_payload` (incl. DHCP/NetBIOS/mDNS), `PingResult`
- `test_config_store.py` — round-trip, modos, versões IP, corrupção JSON, campos ausentes
- `test_history_store.py` — round-trip, ordem cronológica, last_n, clear, hosts(), thread-safety (4 threads × 50 inserts)
- `test_rtt_utils.py` — `rtt_color` (8 boundary cases), `PRIMARY_BTN_STYLE`, `TABLE_STYLE`, `field_label`
- `test_workers.py` — `PingWorker` stop (<200ms), sinais result/stats/loss; `ScanWorker` ports/progress/error/TCP+UDP
- **Importante:** sinais Qt em testes usam `Qt.ConnectionType.DirectConnection` para evitar queued delivery sem event loop

---

## Distribuição

### Executável local
```bash
python -m PyInstaller --onefile --windowed --name NOCPing --icon NOCPing.ico --add-data "NOCPing.ico:." main.py
# Saída: dist/NOCPing.exe
```

### GitHub Actions (`.github/workflows/build.yml`)
Dispara ao criar uma tag `v*` (ex: `git tag v1.1.0 && git push origin v1.1.0`).
Compila automaticamente para Windows, Linux e macOS e publica na página de Releases.
- macOS requer `pip install Pillow` para converter `.ico` → `.icns`

### Versões publicadas
- `v1.0.0` — versão inicial (Monitor, Port Scan, Banner/TLS, Traceroute)
- `v1.1.0` — MTR, histórico SQLite, bandeja+notificações, probes UDP extras, screenshot integrado
- `v1.2.0` — Refatoração de performance, modo WAL no SQLite, melhorias visuais e remoção do minimizar para bandeja
- `v1.3.0` — aba Quick Ping (nova aba inicial), fix de race condition no botão Parar + auto-restart ao trocar de host
- `v1.4.0` — escrita assíncrona no SQLite via fila (`HistoryStore`), throttling de renderização do gráfico RTT (máx. 10 FPS); posteriormente, correção de packet loss e cross-talk entre MTR e Ping via Deep Packet Inspection + PID ICMP único por thread (ver seção **ICMP: PID por thread e Deep Packet Inspection**)

### Repositório
https://github.com/heitortpf/nocping

---

## Pendências / ideias para próximas sessões

- **Notificação de perda de pacote isolada (proposta em aberto, `docs/PLAN.md`):** hoje um único ping falho já marca `HostStatus.DOWN` e dispara notificação, que é sobrescrita 1s depois se o host volta a responder — o usuário nunca vê o alerta de perda pontual. Proposta: adicionar `HostStatus.WARNING`/`DEGRADED` + contador de falhas consecutivas em `HostCard` (só vira `DOWN` após N falhas seguidas), com notificação de bandeja dedicada para o warning. Aguardando decisão do usuário antes de implementar (`docs/PLAN.md` tem as opções detalhadas).
- Ícone da aplicação no macOS como `.icns` nativo (atualmente convertido pelo Pillow no build)
- Empacotamento com instalador (NSIS no Windows, .deb no Linux, .dmg no macOS)
- Mais probes UDP: porta 67 DHCP broadcast (atualmente envia unicast), 5353 multicast real (atualmente envia unicast para o host)
- Notificação de bandeja também para hosts em ERRO (atualmente só UP/DOWN)
- Gráfico do `HistoryDialog` com eixo X em timestamp legível (atualmente índice sequencial)
