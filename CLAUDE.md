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

## Como rodar

```
python main.py
```

Dependências de runtime: `PyQt6`, `pyqtgraph`, `darkdetect`, `qtawesome` (ver `requirements.txt`
para versões mínimas e `pytest`/`pytest-qt` de dev/teste; `pyinstaller` só é necessário para gerar executável).
Python 3.11+ (dev local usa 3.14 no Windows 11).
ICMP e UDP (Monitor, Quick Ping, Traceroute, MTR) requerem execução como Administrador.
Port Scan TCP/UDP **não** requer admin.

---

## Estrutura de arquivos

```
main.py                  — entry point (carrega NOCPing.ico via QIcon)
take_shots.py            — captura automática de screenshots das 6 seções (dark+light) in-process,
                            via MainWindow.show_section()+QWidget.grab() — não usa win32gui/ImageGrab
docs/
  PLAN-features.md       — plano de features executado na v1.1.0
  PLAN.md                — plano em aberto (proposta de status WARNING para perda de pacote isolada, ver seção Pendências)
  DESIGN_SYSTEM.md        — documenta a camada ui/theme/ (tokens + componentes) criada no redesign v2.0.0
  PERFORMANCE.md          — auditoria de performance pós-redesign (profiling do Monitor, throttle do RttGraph, etc.)
  QA_CHECKLIST_v2.md      — checklist de QA da v2.0.0 e o que ficou pendente de validação manual
  baseline/REPORT.md      — auditoria pré-redesign (screenshots + hex colors) usada como referência de "não regredir"
  redesign/VERIFICACAO_FASE3.md
core/
  models.py              — dataclasses e enums (PingResult, ProbeConfig, ProbeMode, IPVersion, HostStatus)
  network.py             — funções de rede puras (sem GUI)
  workers.py             — QThread workers que chamam network.py e emitem sinais PyQt6
  config_store.py        — persistência da lista de hosts monitorados (nocping_hosts.json)
  history_store.py       — singleton SQLite thread-safe (fila assíncrona) para histórico de RTT por host
ui/
  main_window.py         — janela principal, temas, multi-janela, screenshot, sidebar/navegação, shutdown
  quick_ping_tab.py      — aba inicial: orquestrador fino de ping rápido de host único (TCP/ICMP/UDP)
  monitor_tab.py         — aba de monitoramento multi-host estilo vmPing
  scan_tab.py            — aba de port scan TCP/UDP
  banner_tab.py          — aba de banner grab + inspeção TLS/SSL
  traceroute_tab.py      — aba de traceroute ICMP
  mtr_tab.py             — aba MTR (My TraceRoute) com estatísticas contínuas por hop
  theme/
    tokens.py             — fonte única de cores/espaçamento/raio/tipografia (ColorTokens DARK/LIGHT, SPACING, RADIUS, TYPOGRAPHY)
    components.py         — builders de widgets estilizados (primary_button, secondary_button, danger_button, card_frame, section_label, status_badge, count_badge)
  widgets/
    host_card.py           — card individual de host no monitor
    rtt_graph.py            — gráfico de RTT em tempo real
    history_dialog.py       — diálogo de histórico RTT (gráfico + tabela + export CSV)
    sidebar.py               — NavSidebar: navegação vertical por ícones (qtawesome), substitui o QTabWidget do topo
    tray.py                  — SystemTray: ícone de bandeja, menu Abrir/Sair, restauração da janela
    _worker_tab.py           — WorkerTabMixin: cleanup padronizado de QThread worker de execução única (usado por Scan/Banner/Traceroute/MTR)
    _reflow_row.py           — ReflowRow: linha de widgets "toolbar" (grupo esquerda + stretch + grupo direita) que quebra em 2 linhas quando estreita
    quick_ping_control_panel.py — painel de controles do Quick Ping (host/protocolo sempre visíveis; porta/IP/timeout em seção "Avançado" colapsável)
    quick_ping_graph_panel.py   — moldura + RttGraph expandido do Quick Ping
    quick_ping_console.py       — console de log estilo terminal do Quick Ping (toolbar + auto-scroll + cópia + export CSV)
    quick_ping_stats_panel.py   — faixa de status + stat cards (RTT/média/jitter/min/max/perda) do Quick Ping
    _utils.py                — camada legada (rtt_color, field_label, PRIMARY_BTN_STYLE, TABLE_STYLE), hoje reexportando ui/theme/*
tests/
  test_network.py          — testes de core/network.py (CI-safe)
  test_config_store.py     — testes de core/config_store.py
  test_history_store.py    — testes de core/history_store.py (thread-safety)
  test_rtt_utils.py        — testes de ui/widgets/_utils.py
  test_workers.py          — testes de PingWorker e ScanWorker com mocks
  test_ui_navigation.py    — NavSidebar/QStackedWidget, show_section(), lazy-load das 4 abas (pytest-qt)
  test_ui_theme.py         — _toggle_theme() propaga pra todas as janelas + QuickPingTab/HostCard (pytest-qt)
  test_worker_tab_mixin.py — contrato de cleanup do WorkerTabMixin
  test_multi_window_close.py — fechar uma janela secundária não derruba o app inteiro (regressão do bug do QA v2.0.0)
  test_quick_ping_tab.py   — Quick Ping notifica também em ERROR (paridade com o Monitor)
  test_taskbar_icon.py     — _force_native_taskbar_icon() (WM_SETICON direto, ver seção "Barra de tarefas" acima)
  conftest.py              — fixtures isolate_hosts_persistence / clean_main_window_instances para os testes de UI
scripts/
  visual_regression.py     — diff pixel a pixel de screenshots contra um diretório de baseline
screenshots/
  dark/ e light/           — quick_ping.png, monitor.png, portscan.png, banner.png, traceroute.png, mtr.png (um par por tema)
requirements.txt           — runtime + dev/teste (PyQt6, pyqtgraph, darkdetect, qtawesome, pyinstaller, pytest, pytest-qt)
pytest.ini                 — marker "live"; qt_api = pyqt6 fixado
NOCPing.ico                — ícone da aplicação
```

---

## Design system (ui/theme/)

Criado no redesign v2.0.0 para centralizar estilo (documentado em `docs/DESIGN_SYSTEM.md`) — antes disso as cores hex viviam espalhadas e duplicadas entre `ui/main_window.py` e `ui/widgets/_utils.py`.

- `ui/theme/tokens.py` — `ColorTokens` (dataclass frozen) com os campos de superfície/texto/marca/status; instâncias `DARK`/`LIGHT`; também `SPACING`, `RADIUS`, `TYPOGRAPHY`
- `ui/theme/components.py` — builders (`primary_button`, `secondary_button`, `danger_button`, `card_frame`, `section_label`, `status_badge`, `count_badge`) e os mapas `STATUS_COLOR`/`STATUS_LABEL` por `HostStatus`
- `ui/widgets/_utils.py` é a API legada (`rtt_color`, `field_label`, `PRIMARY_BTN_STYLE`, `TABLE_STYLE`) mantida para não quebrar abas existentes, mas implementada por cima destes tokens — código novo deve importar direto de `ui.theme.tokens`/`ui.theme.components`
- **Regra:** nenhum módulo de UI deve declarar cor hex literal para elemento de aplicação. Sempre importar `DARK`/`LIGHT` de `ui.theme.tokens`. Exceção aceita: QSS que usa `palette(...)` do Qt (já segue o tema automaticamente e não precisa de token)
- Ícones vêm de `qtawesome` (`qta.icon(...)`) — ele "queima" a cor no momento da criação, então widgets que recolorem ícone por estado (ex.: `NavSidebar`) precisam recriar o `QIcon` a cada mudança, não existe re-tintagem automática via QSS como em texto

---

## Sistema de temas (ui/main_window.py)

- Autodetect via `darkdetect.isDark()`; fallback por luminosidade do QPalette (`detect_system_dark()`)
- `DARK_PALETTE`/`LIGHT_PALETTE` são gerados a partir de `ColorTokens` via `_palette_dict(t)` — mapeiam `QPalette.ColorRole → hex` lendo os tokens de `ui/theme/tokens.py`, não mais dicts hex hardcoded
- `apply_theme(app, dark)` — define palette + stylesheet global (`_build_stylesheet`)
- `_build_stylesheet(dark)` — gera CSS dinâmico com f-string a partir dos tokens; inclui setas do QSpinBox como PNGs gerados em runtime via QPainter, cacheadas em `_arrow_cache`
- `_toggle_theme()` itera `MainWindow._instances`, chama `apply_theme()` global + `win._apply_window_theme()` (menu/status bar) + `win._quick_ping.apply_theme(dark)` + `card._graph.apply_theme(dark)` em cada `HostCard` do Monitor de cada janela

### Multi-janela
- `MainWindow._instances: list["MainWindow"]` — lista de classe com todas as janelas abertas
- `Ctrl+N` abre nova janela herdando o tema da janela atual
- `_toggle_theme()` itera `_instances` e aplica o tema em todas

### Navegação por sidebar
- `NavSidebar` (`ui/widgets/sidebar.py`) substitui a antiga `QTabBar` no topo — botões checkable exclusivos (`QButtonGroup`) numa coluna à esquerda, emitindo `page_changed(index)`; o conteúdo fica num `QStackedWidget` ao lado
- `MainWindow.SECTIONS` — tupla `("quick_ping", "monitor", "port_scan", "banner_tls", "traceroute", "mtr")`: única fonte de verdade pra ordem/índice das seções
- `MainWindow.show_section(name: str)` — API única de navegação programática (usada por `take_shots.py`); resolve `name` pra índice via `SECTIONS`, seleciona na sidebar e dispara `_on_tab_activated`
- `_on_tab_activated(index)` faz o lazy-load: Port Scan/Banner/Traceroute/MTR (índices 2–5) só instanciam sua `*Tab` na primeira ativação (`_initialized_tabs: set[int]`), substituindo o placeholder `QWidget()` no stack; Quick Ping/Monitor (0/1) são eager desde o `__init__`

### Screenshot integrado
`Arquivo → Salvar Screenshot...` (atalho `Ctrl+P`) usa `QScreen.grabWindow(self.winId())`.
Necessário porque o NOCPing roda como Administrador e o UIPI do Windows impede ferramentas de captura de menor privilégio (Snipping Tool, PrintScreen) de capturar a janela. A captura interna roda no mesmo processo, contorna o problema sem sacrificar desempenho.

### Barra de tarefas: WM_SETICON direto
`_force_native_taskbar_icon(win)` (`ui/main_window.py`, chamada via
`QTimer.singleShot(0, ...)` no fim de `MainWindow.__init__`) define o `HICON`
da janela via `WM_SETICON` direto pela API do Windows (`ctypes`), ignorando
`QIcon`/`QApplication.setWindowIcon()`/`QWidget.setWindowIcon()`. Achado numa
sessão real de troubleshooting: numa instalação Windows específica, nenhum
dos dois caminhos normais do Qt fazia o ícone da janela **rodando** (não
fixada) aparecer certo na barra de tarefas — ficava genérico — mesmo com o
`NOCPing.ico` e o recurso de ícone do `.exe` corretos (confirmado fixando o
app na barra, que extrai o ícone direto do arquivo e mostrava certo; então
não era o arquivo, era a associação em runtime). `WM_SETICON` é o mecanismo
Win32 mais baixo nível pra isso, funciona como rede de segurança quando os
caminhos normais do Qt falham silenciosamente por algum motivo do ambiente.
Não-Windows: no-op. Testes em `tests/test_taskbar_icon.py`.

### Bandeja do sistema
- `ui/widgets/tray.py` — `SystemTray(QSystemTrayIcon)` encapsula ícone/menu ("Abrir NOCPing"/"Sair")/restauração da janela por duplo-clique; `MainWindow._build_tray()` só instancia `self._tray = SystemTray(...)`
- A decisão de **quando** notificar continua em `MainWindow` (é lógica de negócio, não da bandeja): `_on_host_status_changed`/`_on_quick_ping_finished`/`_on_scan_finished`/`_on_banner_finished`/`_on_traceroute_finished`/`_on_mtr_finished` chamam `self._tray.showMessage(...)`
- Notificações ativáveis/desativáveis em `Visualizar → Notificações de host` (checkable QAction), persistidas via `QSettings("NOCPing", "NOCPing")` (chave `notifications_enabled`)
- Sinais de host: `MonitorTab.host_status_changed` (repassa `HostCard.status_changed`, emitido em `_set_status()` para UP/DOWN/ERROR) e `QuickPingTab.host_status_changed` (emitido em `_on_result`/`_on_error`, ver seção Quick Ping) — ambos conectados em `_build_tabs()`

### closeEvent / _shutdown
**Fix v2.0.0:** antes, `closeEvent` chamava `QApplication.quit()` incondicionalmente em qualquer janela — fechar uma janela secundária aberta via `Ctrl+N` derrubava o app inteiro, inclusive a principal e os hosts sendo monitorados nela (bug achado no QA da v2.0.0, coberto por `tests/test_multi_window_close.py`). Agora:

- `closeEvent` chama `self._cleanup_window()` (para todos os workers **desta** janela), remove `self` de `MainWindow._instances`, esconde o tray, e só chama `QApplication.quit()` se `_instances` ficou vazia (ou seja, era a última janela aberta)
- `_cleanup_window()` é idempotente (guard `self._cleaned_up`) — para `self._quick_ping`, cada `card` do Monitor, e Scan/Banner (via `_cleanup_worker()` do `WorkerTabMixin`) / Traceroute/MTR (`stop()` + `wait(500)` inline) só se essas abas já tiverem sido inicializadas (`if self._scan`, etc. — podem ser `None` se a aba nunca foi aberta)
- `QApplication.aboutToQuit` está conectado a `_shutdown()` em **cada** `MainWindow.__init__` — cobre tanto o caminho comum (última janela já chamou `quit()`, `_instances` já vazia) quanto atalhos que pulam `closeEvent` inteiramente ("Sair" no menu Arquivo e "Sair" no menu da bandeja chamam `QApplication.quit()` direto). `_shutdown()` itera `_instances` restantes chamando `_cleanup_window()` em cada uma, e por fim fecha a conexão global do `HistoryStore` (`HistoryStore.instance().close()`, seguro chamar mais de uma vez)

---

## WorkerTabMixin (ui/widgets/_worker_tab.py)

As 4 abas de execução única (`ScanTab`, `BannerTab`, `TracerouteTab`, `MTRTab`) herdam `WorkerTabMixin` para padronizar o desligamento seguro do worker: desconectar sinais, sinalizar parada, aguardar e agendar `deleteLater()`.

- Cada aba implementa `_worker_signal_pairs() -> list[tuple[str, str]]` (pares nome-do-sinal/nome-do-slot, na ordem original de disconnect) — a única customização obrigatória
- `_stop_worker()` (default: `self._worker.stop()`) e as constantes de classe `_WORKER_WAIT_MS`/`_WORKER_WAIT_GUARDED` podem ser sobrescritas por aba para preservar divergências que já existiam antes do mixin (timeout de espera, se checa `isRunning()` antes de parar)
- `_cleanup_worker()` — chamado no fechamento de janela e ao trocar de host — é o método público usado por `MainWindow._cleanup_window()`
- Achado de robustez do `except RuntimeError` (desconectar slot nunca conectado levanta `TypeError` no PyQt6, não coberto) — detalhes em `test_worker_tab_mixin.py`, ver seção Testes automatizados

---

## Quick Ping (ui/quick_ping_tab.py)

Aba inicial da aplicação (desde v1.3.0) — diagnóstico ágil de um único host, independente do Monitor.

`QuickPingTab` é hoje um **orquestrador fino** (extraído no redesign v2.0.0): monta 4 widgets de `ui/widgets/` e conecta o `PingWorker` a eles. O estado de negócio (contadores O(1), jitter via stdev, ciclo de vida do worker) continua em `QuickPingTab` — os widgets só renderizam o que recebem.

- `quick_ping_control_panel.py` — host/protocolo/botões sempre visíveis; porta/versão IP/contagem/timeout/intervalo numa seção "Avançado" colapsável (fechada por padrão)
- `quick_ping_graph_panel.py` — moldura + `RttGraph` expandido (import de pyqtgraph adiado via `QTimer.singleShot(0, ...)` até depois do primeiro paint)
- `quick_ping_console.py` — console estilo terminal (toolbar recolher/Limpar/Copiar/CSV) com auto-scroll e cópia; exportação de CSV só emite `export_requested`, quem sabe o que exportar é o orquestrador
- `quick_ping_stats_panel.py` — faixa de status compacta + stat cards em destaque (RTT atual, média, jitter, mínimo, máximo, perda)
- Suporta TCP/ICMP/UDP
- Ao iniciar um novo ping (mudar IP/host), o worker anterior é parado automaticamente (`_kill_worker`) e o console é limpo antes do novo teste começar — evita a race condition do botão "Parar" (corrigida na v1.3.0)
- Usa `threading.get_ident() & 0xFFFF` como PID ICMP único da thread — ver seção **ICMP: PID por thread e Deep Packet Inspection** abaixo, pois esta aba compartilha `icmp_ping_once()` com o Monitor e pode sofrer cross-talk se essa regra for quebrada
- **Paridade de notificação com o Monitor (v2.0.0, `tests/test_quick_ping_tab.py`):** `_on_error` também emite `host_status_changed(host, old, HostStatus.ERROR)`, igual `HostCard._set_status` já fazia — antes só transições UP/DOWN (via `_on_result`) notificavam, um erro de configuração/privilégio (ex. ICMP/UDP sem Admin) ficava só no console, sem notificação de bandeja

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
`_cleanup_worker()`, herdado de `WorkerTabMixin` (ver seção acima) por todas as 4 abas lazy incluindo `ScanTab`: desconecta sinais, para o worker, aguarda e agenda `deleteLater()`. Padrão obrigatório para evitar sinais duplicados.

---

## Monitor de hosts (ui/monitor_tab.py + ui/widgets/host_card.py)

- Adiciona `HostCard` por host; cada card tem seu `PingWorker`
- Layout de cards: `_FlowLayout` (definida diretamente em `monitor_tab.py`, não um arquivo separado) — quebra linha automaticamente
- Linha de ações globais (exportar CSV/JSON etc.) usa `ReflowRow` (`ui/widgets/_reflow_row.py`), não `FlowLayout` — precisa do `addStretch()` que empurra um grupo pro fim da linha, algo que `FlowLayout` não modela
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

## ICMP: PID por worker e Deep Packet Inspection (core/network.py + core/workers.py)

### Problema histórico resolvido
Um socket ICMP raw recebe **todas** as respostas ICMP do sistema, não só as do processo. Com Quick Ping, Monitor e MTR rodando ao mesmo tempo (cada um em sua própria `QThread`), uma resposta destinada a uma aba podia ser lida por outra, causando perda de pacote reportada indevidamente e cross-talk de RTT entre abas.

### Solução
- Cada worker que envia ICMP (`PingWorker`, `TracerouteWorker`, `MTRWorker`) pega um identificador único via `_next_icmp_pid()` (`core/workers.py` — contador global `itertools.count` protegido por lock) — **não** `threading.get_ident()`: o Windows recicla IDs de thread do SO entre `QThread`s de vida curta, o que podia colidir com o PID de outro worker ainda vivo; um contador monotônico garante unicidade real por worker, independente de o SO reaproveitar a thread.
- `icmp_ping_once()` e `traceroute_hop()` (`core/network.py`) fazem **Deep Packet Inspection**: para pacotes Echo Reply, o `pid`/`seq` do cabeçalho ICMP são comparados diretamente; para erros ICMP (Time Exceeded, Destination Unreachable), o `pid`/`seq` originais são extraídos do payload interno (pacote IP+ICMP encapsulado no corpo do erro) e comparados — um pacote só é aceito se `pid` **e** `seq` baterem com o que foi enviado por aquele worker.
- Ao adicionar qualquer novo caminho que envie ICMP, sempre pegar o PID via `_next_icmp_pid()` (nunca `threading.get_ident()`, nunca um valor fixo/compartilhado) e sempre filtrar respostas por `pid`+`seq` antes de aceitá-las — do contrário reintroduz o bug de cross-talk entre abas.

### Firewall do Windows: ICMPv4 Time Exceeded
Sintoma parecido mas causa totalmente diferente: MTR/Traceroute mostrando `* * *` em **todos** os saltos intermediários, só o salto final (Echo Reply) com dado real. Não é bug de PID/DPI — o conjunto de regras padrão do Firewall do Windows libera entrada de ICMPv6 Time Exceeded mas não tem equivalente pra ICMPv4 (tipo 11); sem essa regra, a resposta dos roteadores intermediários é descartada pelo firewall antes de chegar no raw socket (`tracert`/`ping` nativos não sofrem disso por usarem a API `ICMP.SYS`, fora da mesma avaliação de regras). `ensure_icmp_time_exceeded_firewall_rule()` (`core/network.py`) cria essa regra via `netsh` — chamada por `TracerouteWorker`/`MTRWorker` logo após `is_admin()` passar (mesmo processo já precisa de admin pra rodar essas abas), com guard de módulo (`_firewall_rule_ensured`) pra tentar no máximo uma vez por processo, e falha silenciosamente (nunca deve impedir MTR/Traceroute de rodar — ver README.md, seção "MTR/Traceroute só mostra o salto final", pro fix manual caso a criação automática falhe).

---

## Layouts e alinhamento

- Painéis de controle (Monitor, Traceroute) usam `QGridLayout` com linha 0 = rótulos e linha 1 = campos
- Port Scan e a linha de ações do Monitor usam `ReflowRow` (`ui/widgets/_reflow_row.py`) para ser responsivo — grupo à esquerda, `addStretch()`, grupo à direita empurrado pro fim, quebrando em 2 linhas quando a largura não comporta tudo sem comprimir
- Cor de rótulos: `color:#9ca3af` (estilo fixo, decorativo — não usar palette aqui)

---

## Testes automatizados

```bash
pytest tests/ -v -m "not live"   # CI-safe (sem rede/admin)
pytest tests/ -v                  # completo (requer rede/admin)
```

- `test_network.py` — `_parse_ports`, `_build_icmp_echo`, `calc_stats`, `_get_udp_payload` (incl. DHCP/NetBIOS/mDNS), `PingResult`
- `test_config_store.py` — round-trip, modos, versões IP, corrupção JSON, campos ausentes
- `test_history_store.py` — round-trip, ordem cronológica, last_n, clear, hosts(), thread-safety (4 threads × 50 inserts)
- `test_rtt_utils.py` — `rtt_color` (8 boundary cases), `PRIMARY_BTN_STYLE`, `TABLE_STYLE`, `field_label`
- `test_workers.py` — `PingWorker` stop (<200ms), sinais result/stats/loss; `ScanWorker` ports/progress/error/TCP+UDP
- `test_ui_navigation.py` — `NavSidebar` troca o painel do `QStackedWidget` (`MainWindow._on_tab_activated`), `show_section()` sincroniza sidebar+stack, e as 4 abas lazy (Scan/Banner/Traceroute/MTR) só constroem `__init__` no primeiro clique (spy via `monkeypatch.setattr(cls, "__init__", ...)`), nunca de novo depois
- `test_ui_theme.py` — `MainWindow._toggle_theme()` não lança exceção (com `HostCard` real incluso), propaga pra todas as `MainWindow._instances` abertas (não só a janela onde o botão foi clicado), e chama `apply_theme()` em `QuickPingTab` e em `card._graph` de cada `HostCard` do Monitor
- `test_worker_tab_mixin.py` — `WorkerTabMixin._cleanup_worker()` desconecta sinais, chama `stop()`+`wait()` só quando `isRunning()` (modo guardado, default) ou sempre (`_WORKER_WAIT_GUARDED=False`), e é seguro chamar 2x seguidas; usa um `QThread` fake com sinais reais do PyQt6 (não `Mock`, pois testa a semântica real de `disconnect()`). **Achado durante a escrita destes testes:** o `except RuntimeError` em `_cleanup_worker()` não cobre o caso de desconectar um slot nunca conectado — o PyQt6 levanta `TypeError` nesse caso, não `RuntimeError`. Não afeta as 4 abas reais (sempre conectam os sinais antes de qualquer cleanup), mas fica pinado em `test_cleanup_swallows_disconnect_typeerror_from_unconnected_slot`
- `test_multi_window_close.py` — valida o fix do bug de `closeEvent` (v2.0.0, ver seção `closeEvent / _shutdown` acima): fechar uma janela secundária só limpa e remove aquela janela; `QApplication.quit()` (mockado no teste) só é chamado quando é a última. Usa `qtbot` + `isolate_hosts_persistence`/`clean_main_window_instances`
- `test_quick_ping_tab.py` — `QuickPingTab` emite `host_status_changed` também em `ERROR` (paridade com `HostCard`, ver seção Quick Ping acima)
- `test_taskbar_icon.py` — `_force_native_taskbar_icon()` chama `WM_SETICON` via ctypes só no Windows, ignora se o `.ico` não existe, engole exceção se a janela ainda não tem HWND nativo, e não manda `SendMessageW` se `LoadImageW` falhar; `ctypes.windll` é mockado com `monkeypatch.setattr(ctypes, "windll", fake, raising=False)` pra rodar em qualquer SO (o atributo só existe de verdade no Windows)
- `conftest.py` — fixtures `isolate_hosts_persistence` (substitui `ui.monitor_tab.load_hosts`/`save_hosts` por no-ops — sem isso os testes de UI leriam/sobrescreveriam o `nocping_hosts.json` real da máquina) e `clean_main_window_instances` (salva/restaura `MainWindow._instances` ao redor do teste, já que é uma lista de classe compartilhada); não são `autouse`, só os testes que instanciam `MainWindow`/`MonitorTab` de verdade precisam pedi-las
- **Importante:** sinais Qt em testes usam `Qt.ConnectionType.DirectConnection` para evitar queued delivery sem event loop
- **Testes de UI (`test_ui_navigation.py`, `test_ui_theme.py`) usam [pytest-qt](https://pytest-qt.readthedocs.io/)** (fixture `qtbot`) e instanciam `MainWindow` de verdade — **precisam de um display**. Em Linux headless/CI, rodar sob `xvfb-run -a pytest tests/ -v -m "not live"` (ou exportar `DISPLAY` de um `Xvfb` já iniciado); Windows/macOS não precisam disso. `qt_api = pyqt6` está fixado em `pytest.ini` para não depender de qual binding Qt está instalado. Fixtures `isolate_hosts_persistence`/`clean_main_window_instances` em `tests/conftest.py` evitam que esses testes leiam/gravem o `nocping_hosts.json` real da máquina ou vazem `MainWindow._instances` entre testes.
- **Regressão visual:** `scripts/visual_regression.py` (fora da suíte `pytest`) roda `take_shots.py` e compara pixel a pixel contra um diretório de baseline (`--baseline-dir`, default `docs/baseline/screenshots-pre/` — pré-redesign, então sempre vai reportar diff alto; para gate de regressão futura usar `docs/redesign/screenshots-post/`), com tolerância configurável (`--tolerance`, padrão 2%) e exit code não-zero se algo passar do threshold.

---

## Distribuição

### Executável local
```bash
python -m PyInstaller --onefile --windowed --noupx --name NOCPing --icon NOCPing.ico --collect-data qtawesome --add-data "NOCPing.ico:." main.py
# Saída: dist/NOCPing.exe
```
`--collect-data qtawesome` é obrigatório desde que `qtawesome` virou dependência
(design system, v2.0.0) — ele carrega fontes de ícone (`.ttf`+`.json`) em
runtime, que a análise estática do PyInstaller não detecta sozinha. Sem essa
flag o executável builda normalmente mas crasha ao abrir
(`ModuleNotFoundError: No module named 'qtawesome'` se a dependência também
não estiver instalada no ambiente de build — foi o caso do binário publicado
inicialmente como v2.0.0, corrigido antes do release final).

`--noupx` evita compressão UPX (um dos heurísticos mais comuns de
falso-positivo de antivírus em builds PyInstaller) — não é a causa raiz do
Windows Defender colocando o exe em quarentena (o exe não é assinado
digitalmente, essa é a causa; ver README.md, seção "Windows Defender /
SmartScreen"), mas remove uma variável a mais.

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
- `v1.5.0` — notificações de bandeja para todas as abas (conclusão/erro de Port Scan, Traceroute, Banner Grab, MTR), Quick Ping ganha alertas ao vivo de UP/DOWN
- `v2.0.0` — redesign visual completo em cima de `ui/theme/` (tokens + componentes, ícones via qtawesome); navegação por `NavSidebar` no lugar do `QTabWidget` do topo; `quick_ping_tab.py` quebrada em 4 widgets dedicados + `WorkerTabMixin` unificando o shutdown de Scan/Banner/Traceroute/MTR + `MainWindow.show_section()` como API única de navegação programática; renderização em lotes do Port Scan (10Hz) com limite de 5000 linhas na tabela ao vivo; suíte de testes de UI com pytest-qt; fix do bug em que fechar uma janela secundária derrubava o app inteiro (ver seção `closeEvent / _shutdown`); Quick Ping passa a notificar também em ERROR
- `v2.0.1` — fix de MTR/Traceroute só mostrando o salto final em redes "Públicas" do Windows (falta regra de firewall ICMPv4 Time Exceeded, criada automaticamente agora — ver seção "Firewall do Windows: ICMPv4 Time Exceeded"); fix de ícone genérico na barra de tarefas via `WM_SETICON` direto (ver seção "Barra de tarefas: WM_SETICON direto"); `--noupx` no build; documentação do falso-positivo do Windows Defender no README
- `v2.0.2` — auto-preenchimento de `host:porta` (TCP) no Quick Ping e no Monitor (`ui/widgets/_utils.py::parse_host_port`); `LICENSE` (MIT) adicionado de verdade ao repo (o badge/seção do README já citava MIT, mas não existia arquivo — corrigido); documentação do bloqueio por Mark of the Web / Controle de Aplicativo no README

### Repositório
https://github.com/heitortpf/nocping

---

## Pendências / ideias para próximas sessões

- **Assinatura de código do `.exe` via SignPath.io (decidido em sessão de 2026-08-09):** usuário escolheu o programa gratuito Open Source do [SignPath](https://signpath.io) em vez de Azure Trusted Signing pago ou de só documentar o contorno manual. Pré-requisitos pro programa (repo público + licença OSI-aprovada) já estão prontos (`LICENSE` MIT adicionado na v2.0.2). **Próximo passo é do usuário:** aplicar em signpath.io pro plano Open Source/Foundation com o link do repo; a aprovação é manual e não instantânea. Depois de aprovado, o dashboard do SignPath gera um snippet de workflow específico do projeto (org-id/project-slug/signing-policy-slug) — usar esse snippet como referência pra adicionar um step de assinatura em `.github/workflows/build.yml` (só no leg `windows-latest` do job `build`, assinando `dist/NOCPing.exe` antes do upload do artefato), guardado atrás de `if: secrets.SIGNPATH_API_TOKEN != ''` pra não quebrar o build atual enquanto os secrets não existirem. Não implementado ainda nesta sessão — não escrevi YAML especulativo pro `build.yml` sem os valores reais do projeto aprovado.
- **Notificação de perda de pacote isolada (proposta em aberto, `docs/PLAN.md`):** hoje um único ping falho já marca `HostStatus.DOWN` e dispara notificação, que é sobrescrita 1s depois se o host volta a responder — o usuário nunca vê o alerta de perda pontual. Proposta: adicionar `HostStatus.WARNING`/`DEGRADED` + contador de falhas consecutivas em `HostCard` (só vira `DOWN` após N falhas seguidas), com notificação de bandeja dedicada para o warning. Aguardando decisão do usuário antes de implementar (`docs/PLAN.md` tem as opções detalhadas).
- Ícone da aplicação no macOS como `.icns` nativo (atualmente convertido pelo Pillow no build)
- Empacotamento com instalador (NSIS no Windows, .deb no Linux, .dmg no macOS)
- Mais probes UDP: porta 67 DHCP broadcast (atualmente envia unicast), 5353 multicast real (atualmente envia unicast para o host)
- Gráfico do `HistoryDialog` com eixo X em timestamp legível (atualmente índice sequencial)
- **Validar manualmente Windows com admin, Linux com root e macOS/Gatekeeper na v2.0.0** (build já publicado; UI não toca em `core/network.py`, risco baixo, mas fica pendente confirmar) — ver `docs/QA_CHECKLIST_v2.md` (Seções 1.1, 2, 3), que documenta exatamente o que não foi verificado nesta sessão e a justificativa de risco pra taguear mesmo assim.
