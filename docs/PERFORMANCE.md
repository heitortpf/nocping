# Auditoria de performance — NOCPing (pós-redesign Fase 3)

Gerado em 2026-07-24, depois do redesign visual completo (Fases 2–3.7) e do
fix de responsividade do Port Scan/Monitor. Compara com
`docs/baseline/REPORT.md` (pré-redesign) onde aplicável. Escopo: os 5 pontos
abaixo — profiling do Monitor com 50 hosts, confirmação do throttle do
gráfico de RTT, renderização incremental do Port Scan, este relatório, e
`pytest`.

## Metodologia geral

Ambiente de desenvolvimento (não é a máquina de produção do analista NOC) —
os números absolutos servem para comparação relativa (antes/depois, ranking
de custo), não como SLA. `cProfile` (stdlib) foi usado para o profiling —
`py-spy` não está disponível no ambiente. Todos os scripts de profiling/
benchmark rodaram fora do repo (scratchpad) e não alteraram
`nocping_hosts.json`/`nocping_history.db` (backup/restore + diff antes/depois
de cada rodada, como já era prática nas etapas anteriores desta sessão).

---

## 1. Profiling do Monitor com 50 hosts

### Metodologia

O pedido original era "50 hosts em modo ICMP". Neste ambiente sem
privilégios de Administrador, um `PingWorker` real em modo ICMP só emitiria
`error` imediatamente (checagem `is_admin()` em `core/workers.py`) — não
gera carga sustentada, e mediria "quão rápido o app desiste", não o custo de
UI sob monitoramento ativo. Para isolar o que a auditoria realmente pede
("os 5 maiores consumidores de CPU na UI thread"), o profiling injeta
`PingResult` sintéticos diretamente em `HostCard._on_result()` — mesmo
caminho de código que um `PingWorker` real dispararia via signal, mas sem
custo de rede/socket, que não é "UI thread" e mediria a rede do ambiente de
teste, não o app.

50 `HostCard`s em modo ICMP (config idêntica à real) + 2 hosts já
persistidos de sessões anteriores (`nocping_hosts.json`, ambiente de dev) =
52 cards. 20 rodadas de resultado sintético por card (1040 chamadas de
`_on_result`, ~5% de perda simulada), com `app.processEvents()` entre
rodadas para permitir que timers/paint realmente disparem. `cProfile`
habilitado só durante as 20 rodadas medidas (1 rodada de aquecimento fora).

Rodado 3x para checar estabilidade do ranking — o tempo total variou
(1.4–1.7s para 1040 eventos, ambiente com ruído de fundo não controlado),
mas o **ranking relativo por `tottime` foi consistente nas 3 execuções**.

### Top 5 consumidores de CPU (self-time, exclui sub-chamadas)

| # | Função | Chamadas | % do tempo próprio total | Causa |
|---|---|---:|---:|---|
| 1 | `QWidget.setStyleSheet` (built-in) | 6240 (=1040×6) | ~20% | `HostCard._on_result()` chama `setStyleSheet()` 4x por resultado (`_val_rtt`, `_val_avg`, `_val_jitter`, `_val_loss`, recolorindo por `rtt_color()`) + `_set_status()` chama mais 2x (`_indicator`, `_lbl_status_text`) quando o status muda — Qt reparseia a stylesheet inteira daquele widget a cada chamada. **Padrão pré-existente**, não introduzido pelo redesign desta sessão (já era a técnica usada antes para colorir texto por valor); o redesign manteve a mesma abordagem em `_val_avg`/`_val_jitter`/`_val_loss` e no `quick_ping_stats_panel.py` equivalente. |
| 2 | `QCoreApplication.processEvents` (built-in) | 20 | ~15% | Custo do próprio loop de eventos do Qt processando os `pyqtSignal.emit()` + repaints de 52 cards simultâneos — baseline esperado do harness de teste, não um bug de app. |
| 3 | `sqlite3.Connection.commit` | 40 | ~3–7%¹ | `HistoryStore._db_worker` (fila assíncrona, v1.4.0) — já otimizado por design; 40 commits para 1040 registros bate com o batching (`_BATCH_SIZE=50`). Não é um consumidor da **UI thread** propriamente (roda em thread dedicada), aparece no profile porque a fila é alimentada síncronamente por `HostCard._on_result()`. |
| 4 | `pyqtgraph.functions.mkPen` / `mkColor` | ~3600–5400 | ~2–3% cada | `RttGraph._redraw()` (chamado a cada tick do `_redraw_timer`) cria um `QPen`/`QBrush` **novo** a cada redraw em vez de cachear/reusar — ver seção 2. |
| 5 | `statistics._ss` (usado por `statistics.stdev`) | ~1000–1040 | ~1–2% | `HostCard._on_result()` recalcula o jitter via `statistics.stdev(self._recent_rtts)` (deque de até 50 valores) **a cada resultado**, mesmo padrão do Quick Ping. O(n) por chamada, n≤50 — barato isoladamente, mas some em 1040 chamadas. |

¹ variou entre execuções conforme o thread de I/O do SQLite competia com o
event loop; consistentemente presente no top 5 nas 3 execuções.

Uma entrada adicional (`built-in method play`, 64–87 chamadas, ~2–3%) apareceu
nas 3 execuções mas não corresponde a nenhuma chamada em código do app
(nenhum uso de `QSound`/`QMediaPlayer`/`QPropertyAnimation` no repo) — provável
mecanismo interno do Qt/pyqtgraph (estilo/animação), não investigado a fundo
por não ser acionável a partir do código do NOCPing.

### Leitura

Nenhum dos 5 é uma regressão do redesign — `setStyleSheet`-por-atualização,
o cálculo de jitter e a fila assíncrona do SQLite já existiam antes desta
sessão (jitter no Monitor é a única peça **nova**, adicionada durante o
redesign do `HostCard`, mas replica um padrão já existente no Quick Ping).
`card_frame()`/demais builders de `ui/theme/components.py` **não** aparecem
no profile — confirmado também por inspeção estática (seção 2) que são
chamados só na construção do widget, nunca em `_on_result`/hot path.

**Não implementado nesta auditoria** (fora do escopo pedido — os itens 1 e 2
são de diagnóstico, não de correção): trocar `setStyleSheet()` por
`QGraphicsColorizeEffect`/paleta customizada por widget reduziria o custo #1,
e cachear os `QPen`/`QBrush` por cor em `RttGraph` (ao invés de recriar em
todo redraw) reduziria #4. Ambos ficam registrados aqui como candidatos para
uma eventual sessão de otimização do Monitor, caso o usuário priorize.

---

## 2. Confirmação do throttle de `rtt_graph.py`

`ui/widgets/rtt_graph.py` **não foi tocado** por nenhuma tarefa de redesign
desta sessão — confirmado por `git diff` (arquivo não aparece em `git status
--short`). Leitura direta do arquivo confirma o mecanismo intacto:

- `_redraw_timer` — `QTimer(self)`, `setInterval(100)` (10 FPS), conectado a
  `_throttled_redraw`, iniciado no `__init__`.
- `add_point()` só marca `self._needs_redraw = True` — não redesenha na hora.
- `_throttled_redraw()` só chama `_redraw()` real se `self._needs_redraw and
  self.isVisible()` — gráficos de abas/cards fora de tela não gastam CPU.

Confirmado também no profiling da seção 1: `_redraw` foi chamado 660–770
vezes em ~1040 eventos de `add_point()` (não 1:1) — o throttle está de fato
reduzindo o número de redesenhos reais.

**Ressalva encontrada (não é regressão, é uma característica do design que
vale documentar):** o throttle de 10 FPS é **por widget**, não global. Com
52 `RttGraph`s todos visíveis simultaneamente (grade do Monitor), o sistema
como um todo pode redesenhar até ~520 vezes/segundo (52 × 10 Hz), não 10
vezes/segundo. Isso é consistente com o texto do `CLAUDE.md`
("`_redraw_timer` limita **o** redesenho a no máximo 10 FPS", no singular,
por instância) — não é um bug, mas é uma nuance que só aparece com dezenas
de hosts simultâneos, cenário que esta auditoria foi a primeira a testar
explicitamente. Nenhuma mudança foi feita — registrado aqui como observação,
não como problema a corrigir sem pedido explícito.

Nenhum builder de `ui/theme/components.py` (`card_frame`, `stat_card`,
`primary_button`, etc.) é chamado dentro de um hot path de atualização —
confirmado via `grep` de todas as chamadas de `card_frame(` no projeto:
todas ocorrem dentro de métodos `_build_ui()`, executados uma única vez na
construção do widget.

---

## 3. Port Scan — renderização incremental no preset "Todas (1-65535)"

### Problema identificado

`core/network.py`/`ScanWorker` (não tocados, fora de escopo) já emitem
`port_result`/`progress` por porta de forma assíncrona e eficiente via
`asyncio` — o gargalo estava inteiramente na camada de UI (`ui/scan_tab.py`):

- `_on_progress()` chamava `self._progress.setValue(done)` **a cada** sinal
  — com "Todas" isso é até 65535 chamadas (131070 em TCP+UDP), cada uma
  cruzando thread (`QueuedConnection` implícito do `pyqtSignal` entre
  `QThread` e a UI thread) e disparando repaint da progress bar.
- `_on_port_result()` só insere linha na tabela para portas abertas (ou
  "open|filtered" em UDP com o checkbox marcado) — na maioria dos scans o
  volume de linhas é pequeno. **Mas** em UDP sem resposta (comportamento
  típico do protocolo), com "UDP open|filtered" marcado, praticamente
  **todas** as 65535 portas podem virar uma linha — o pior caso realista do
  preset "Todas".
- Cada inserção chamava `self._table.scrollToBottom()` individualmente —
  caro em uma `QTableWidget` que já tem milhares de linhas.

### Benchmark do estado anterior ao fix (medido, não estimado)

Simulação do pior caso (65535 portas UDP, todas "open|filtered", igual ao
código anterior — `insertRow` + `scrollToBottom` + `setValue` por evento,
sem lote): **~70 segundos** para popular a tabela inteira, bloqueando a UI
thread de forma síncrona durante esse tempo inteiro (nenhum repaint, nenhum
clique em "Parar" processado até terminar).

### Fix implementado (`ui/scan_tab.py`)

1. **Buffer + `QTimer` de 100ms (10 Hz)** — mesmo padrão já usado em
   `RttGraph._redraw_timer`. `_on_port_result()`/`_on_progress()` agora só
   empilham em `self._pending_rows`/`self._pending_progress`; um novo
   `_flush_pending()`, chamado pelo timer, esvazia o buffer em lote —
   `setUpdatesEnabled(False)` durante a inserção, um único `scrollToBottom()`
   por lote (não por linha), um único `setValue()` por lote. Isso já evita
   que a UI trave de forma síncrona durante o scan — os sinais são
   absorvidos quase instantaneamente (65535 eventos em ~110–140ms) e a
   tabela vai enchendo em lotes visíveis, sem travar o clique em "Parar".
2. **Limite de 5000 linhas na tabela ao vivo (`_MAX_TABLE_ROWS`)** — o
   benchmark acima mostrou que mesmo em lote, inserir dezenas de milhares de
   `QTableWidgetItem` continua caro no nível do próprio Qt (~1ms/linha
   medido, independente de como os eventos chegam). Só o *buffering* não
   limita o **tempo total** de renderização se o número de resultados for
   realmente grande — então a tabela ao vivo agora para de crescer em 5000
   linhas; `self._results` (usado por "Exportar CSV") continua recebendo
   **todos** os resultados sem truncar. O rótulo "Abertas: N" avisa quando
   isso acontece: `"Abertas: 65535  (exibindo 5000 — CSV tem os 65535)"`.

### Resultado (medido após o fix, mesmo cenário de pior caso)

| Métrica | Antes | Depois |
|---|---:|---:|
| Tempo para absorver 65535 eventos de sinal (sem travar) | — (bloqueava durante a inserção) | ~110–140ms |
| Tempo total até UI estabilizar (pior caso, 65535 "abertas") | ~70000ms, síncrono e bloqueante | ~3900–4100ms, em lotes de 100ms — UI responsiva o tempo todo |
| Linhas na tabela ao vivo (pior caso) | 65535 (sem limite) | 5000 (limitado) |
| Linhas disponíveis via "Exportar CSV" | 65535 | 65535 (sem truncar) |

`core/network.py`, `ScanWorker` e a lógica de scan assíncrono **não foram
alterados** — o fix é inteiramente em `ui/scan_tab.py` (camada de
apresentação), preservando o contrato de sinais existente
(`port_result(int, bool, float, str)`, `progress(int, int)`).

---

## 4. Testes automatizados

```
pytest tests/ -v -m "not live"
77 passed, 3 deselected
```

Sem regressões — nenhum teste existente cobre diretamente `ScanTab`/
`HostCard` (são componentes de UI sem testes unitários dedicados, mesma
situação do baseline pré-redesign), então a validação funcional do fix do
Port Scan foi feita via os benchmarks/asserts descritos na seção 3
(`_table.rowCount() == _MAX_TABLE_ROWS`, `len(_results) == N` sem truncar) e
inspeção manual da aba renderizando corretamente após um scan pequeno real.

---

## Resumo

| Item pedido | Status |
|---|---|
| 1. Profiling Monitor 50 hosts, top 5 CPU | Feito — ver seção 1 |
| 2. Confirmar throttle 10 FPS do RttGraph | Confirmado intacto — ver seção 2 |
| 3. Paginação/renderização incremental no Port Scan "Todas" | Implementado — buffer + `QTimer` 10Hz + limite de 5000 linhas na tabela ao vivo, CSV completo — ver seção 3 |
| 4. `docs/PERFORMANCE.md` | Este arquivo |
| 5. `pytest tests/ -v -m "not live"` | 77 passed, 3 deselected |
