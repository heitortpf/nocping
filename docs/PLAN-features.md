# PLAN — NOCPing: Bug Fixes e Features

**Criado em:** 2026-05-22  
**Escopo:** Bug fix + 3 features de produto. Distribuição/empacotamento fora do escopo.

---

## Visão Geral

| # | Tarefa | Tipo | Esforço | Dependências |
|---|--------|------|---------|--------------|
| T-01 | MTRWorker cleanup no closeEvent | Bug fix | Pequeno (~15 min) | — |
| T-02 | Probes UDP extras (DHCP, NetBIOS, mDNS) | Feature | Pequeno (~1h) | — |
| T-03 | Notificações de sistema (QSystemTrayIcon) | Feature | Médio (~3h) | — |
| T-04 | Histórico persistente de RTT (SQLite) | Feature | Grande (~5h) | — |

---

## T-01 — Bug: MTRWorker não para no closeEvent

**Problema:** `closeEvent` em `ui/main_window.py` encerra `ScanWorker`, `BannerWorker` e `TracerouteWorker`, mas não para o `MTRWorker`. Se a aba MTR estiver rodando ao fechar a janela, o worker continua em background e pode causar acesso a objetos Qt destruídos.

**Arquivo:** `ui/main_window.py` — método `closeEvent` (linha ~324)

**Mudança:**
```python
# Adicionar após o bloco do TracerouteWorker:
if self._mtr._worker and self._mtr._worker.isRunning():
    self._mtr._worker.stop()
    self._mtr._worker.wait(500)
```

**Testes:** Nenhum novo necessário — comportamento de encerramento.

---

## T-02 — Feature: Probes UDP extras

**Contexto:** `_get_udp_payload(port)` em `core/network.py` já tem probes específicos para portas 53, 123 e 161. Adicionar:

| Porta | Protocolo | Payload |
|-------|-----------|---------|
| 67 | DHCP Discover | 300 bytes com magic cookie `63825363` |
| 137 | NetBIOS Name Service | Query de status de nó |
| 5353 | mDNS | Query DNS multicast para `_services._dns-sd._udp.local` |

**Arquivos:**
- `core/network.py` — função `_get_udp_payload`, adicionar 3 novos `if port ==` 
- `tests/test_network.py` — 3 novos casos de teste para os payloads

**Critério de aceite:**
- `_get_udp_payload(67)` retorna bytes com `63825363` (magic cookie DHCP)
- `_get_udp_payload(137)` retorna bytes NetBIOS válidos (primeiros bytes `\x00\x00\x00\x10\x00\x01`)
- `_get_udp_payload(5353)` retorna query DNS para `_services._dns-sd._udp.local`
- Todos passam em `pytest tests/test_network.py -v -m "not live"`

---

## T-03 — Feature: Notificações de sistema (QSystemTrayIcon)

**Objetivo:** Exibir notificação do sistema (balão/toast) quando um host monitorado muda de status `UP → DOWN` ou `DOWN → UP`. Ícone na bandeja do sistema.

### Componentes

**1. Tray icon — `ui/main_window.py`**
- Criar `QSystemTrayIcon` com `NOCPing.ico` no `__init__`
- Menu de contexto: "Abrir", "Sair"
- Método `notify(title, msg, icon_type)` usando `showMessage()`
- Duplo-clique no ícone da bandeja restaura a janela

**2. Sinal de mudança de status — `ui/widgets/host_card.py`**
- `HostCard` já rastreia `_last_status: HostStatus`
- Emitir novo sinal `status_changed(host: str, old: HostStatus, new: HostStatus)` quando o status muda
- Conectar no `MonitorTab._add_card()` → repassar para `MainWindow.notify()`

**3. Configuração — `ui/main_window.py`**
- Checkbox no menu "Notificações" para ativar/desativar globalmente
- Persistir preferência via `QSettings` (chave `nocping/notifications_enabled`)

**Arquivos:**
- `ui/main_window.py` — tray icon, notify(), menu de notificações, QSettings
- `ui/widgets/host_card.py` — sinal `status_changed`, lógica de detecção de mudança
- `ui/monitor_tab.py` — conectar `status_changed` de cada card ao callback externo

**Critério de aceite:**
- Ícone aparece na bandeja ao iniciar
- Notificação disparada ao host mudar de UP→DOWN e DOWN→UP
- Checkbox "Notificações" desativa as mensagens
- Duplo-clique na bandeja restaura a janela

---

## T-04 — Feature: Histórico persistente de RTT (SQLite)

**Objetivo:** Gravar todos os resultados de ping em banco SQLite local e oferecer visualização de histórico por host.

### Arquitetura

**1. Camada de storage — `core/history_store.py` (arquivo novo)**
- `HistoryStore` singleton com conexão SQLite thread-safe (`check_same_thread=False`, `threading.Lock`)
- Banco em `nocping_history.db` na raiz do projeto (ignorado pelo git)
- Schema:
  ```sql
  CREATE TABLE IF NOT EXISTS rtt_history (
      id        INTEGER PRIMARY KEY AUTOINCREMENT,
      host      TEXT NOT NULL,
      ts        REAL NOT NULL,   -- time.time()
      success   INTEGER NOT NULL,
      elapsed   REAL NOT NULL,
      note      TEXT
  );
  CREATE INDEX IF NOT EXISTS idx_host_ts ON rtt_history(host, ts);
  ```
- Métodos: `record(host, result: PingResult)`, `query(host, last_n=500) -> list[dict]`, `clear(host)`

**2. Integração com PingWorker — `ui/widgets/host_card.py`**
- Em `_on_result(r: PingResult)`, chamar `HistoryStore.instance().record(self._host, r)`

**3. Widget de histórico — `ui/widgets/history_dialog.py` (arquivo novo)**
- `QDialog` com gráfico `pyqtgraph` de RTT dos últimos N pontos (seletor: 100 / 500 / 1000 / tudo)
- Tabela abaixo: timestamp, status, RTT, nota
- Botão "Exportar CSV", botão "Limpar histórico"
- Abre via botão "⏱ Histórico" no `HostCard`

**4. Botão no HostCard — `ui/widgets/host_card.py`**
- Adicionar botão "⏱ Histórico" na toolbar do card
- `clicked` → `HistoryDialog(host=self._host).exec()`

**Arquivos:**
- `core/history_store.py` — novo
- `ui/widgets/history_dialog.py` — novo
- `ui/widgets/host_card.py` — integração record + botão
- `tests/test_history_store.py` — novo: round-trip, query, clear, thread-safety básica
- `.gitignore` — adicionar `nocping_history.db`

**Critério de aceite:**
- `nocping_history.db` criado automaticamente ao iniciar a app
- Após 10 pings num host, `HistoryStore.query(host, 10)` retorna 10 registros
- `HistoryDialog` abre, gráfico renderiza, exportar CSV funciona
- `pytest tests/test_history_store.py -v` passa sem rede

---

## Ordem de execução sugerida

```
T-01  →  (independente, 15 min, fazer primeiro)
T-02  →  (independente, pode fazer em paralelo com T-01)
T-03  →  (após T-01 e T-02 estarem estáveis)
T-04  →  (última, mais complexa, base de dados nova)
```

---

## Arquivos que serão tocados (resumo)

| Arquivo | T-01 | T-02 | T-03 | T-04 |
|---------|------|------|------|------|
| `ui/main_window.py` | ✏️ | — | ✏️ | — |
| `core/network.py` | — | ✏️ | — | — |
| `ui/widgets/host_card.py` | — | — | ✏️ | ✏️ |
| `ui/monitor_tab.py` | — | — | ✏️ | — |
| `core/history_store.py` | — | — | — | 🆕 |
| `ui/widgets/history_dialog.py` | — | — | — | 🆕 |
| `tests/test_network.py` | — | ✏️ | — | — |
| `tests/test_history_store.py` | — | — | — | 🆕 |
| `.gitignore` | — | — | — | ✏️ |
