# Baseline pré-redesign — NOCPing

Gerado em 2026-07-24, antes de iniciar o redesign. Nenhum código de produção foi alterado
nesta etapa — apenas leitura, execução de testes e captura de screenshots.

## Artefatos gerados

- `docs/baseline/tests-pre-redesign.txt` — output completo de `pytest tests/ -v -m "not live"`
- `docs/baseline/screenshots-pre/{dark,light}/*.png` — 5 abas (Monitor, Port Scan, Banner/TLS,
  Traceroute, MTR), nos dois temas
- `docs/baseline/hex-colors.txt` — lista completa (199 linhas) de cores hex hardcoded fora de `_utils.py`
- este arquivo

### Nota sobre os screenshots

`take_shots.py` (no repo) **não alterna tema** — ele só clica entre as 5 abas em coordenadas fixas
da tela, assumindo que o app já está aberto no tema atual do SO. Para capturar os dois temas de forma
confiável, sem simular cliques de mouse na tela real do usuário (o script original usa `win32gui` +
cliques absolutos), gerei um script auxiliar temporário (fora do repo) que instancia `MainWindow`
duas vezes em processo, força `apply_theme(app, dark=True/False)` e usa `widget.grab()` por aba —
mesma lista de abas e nomes de arquivo do `take_shots.py` original, só a captura é in-process em vez
de screen-grab externo. Nenhum arquivo do repo foi modificado para isso.

## 1. Testes

```
77 passed, 3 deselected in 1.06s
```

Todos os testes CI-safe (`test_network.py`, `test_config_store.py`, `test_history_store.py`,
`test_rtt_utils.py`, `test_workers.py`) passaram. Ver `tests-pre-redesign.txt` para o output completo,
teste a teste.

## 2. Linhas por arquivo (ui/ e core/)

| Arquivo | Linhas |
|---|---:|
| `ui/quick_ping_tab.py` | 816 |
| `core/network.py` | 712 |
| `ui/main_window.py` | 503 |
| `ui/widgets/host_card.py` | 473 |
| `core/workers.py` | 370 |
| `ui/mtr_tab.py` | 363 |
| `ui/monitor_tab.py` | 362 |
| `ui/scan_tab.py` | 333 |
| `ui/traceroute_tab.py` | 314 |
| `ui/widgets/history_dialog.py` | 246 |
| `ui/banner_tab.py` | 224 |
| `core/history_store.py` | 133 |
| `ui/widgets/rtt_graph.py` | 103 |
| `core/config_store.py` | 49 |
| `core/models.py` | 43 |
| `ui/widgets/_utils.py` | 40 |
| `ui/__init__.py`, `core/__init__.py`, `ui/widgets/__init__.py` | 0 |
| **Total (ui/ + core/)** | **5084** |

`quick_ping_tab.py` é hoje o maior arquivo da UI por uma boa margem (mais que o dobro do segundo
colocado), e concentra layout, workers de conexão e toda a lógica de stats/console em um único
arquivo — candidato natural a divisão caso o redesign mexa nessa aba.

## 3. Cores hex hardcoded em `ui/` fora de `_utils.py`

**199 ocorrências em 10 arquivos** (lista completa em `hex-colors.txt`):

| Arquivo | Ocorrências |
|---|---:|
| `ui/main_window.py` | 61 |
| `ui/quick_ping_tab.py` | 37 |
| `ui/widgets/host_card.py` | 22 |
| `ui/mtr_tab.py` | 19 |
| `ui/traceroute_tab.py` | 16 |
| `ui/scan_tab.py` | 13 |
| `ui/banner_tab.py` | 11 |
| `ui/widgets/history_dialog.py` | 10 |
| `ui/monitor_tab.py` | 5 |
| `ui/widgets/rtt_graph.py` | 5 |

A maior parte em `main_window.py` é esperada (é onde `DARK_PALETTE`/`LIGHT_PALETTE` e o QSS global
são definidos — a fonte da verdade das cores do app). Fora dele, os hex mais repetidos são as cores
semânticas de status/RTT (`#4ade80` verde, `#f87171` vermelho, `#facc15` amarelo, `#6b7280` cinza,
`#9ca3af` cinza claro, `#7c3aed` roxo primário) reescritos literalmente em vez de importados de
`rtt_color()` / constantes compartilhadas — hoje só `host_card.py` e `history_dialog.py` importam
`_rtt_color` de `_utils.py`; `mtr_tab.py`, `traceroute_tab.py`, `scan_tab.py`, `banner_tab.py` e
`quick_ping_tab.py` redefinem os mesmos hex diretamente.

## 4. QSS inline duplicado entre arquivos de aba

| Estilo | Onde já existe centralizado | Reimplementado em | Divergências |
|---|---|---|---|
| Botão de perigo (`#dc2626` / hover `#b91c1c`) | Não existe (`_utils.py` só tem `PRIMARY_BTN_STYLE`) | `monitor_tab.py:124-126`, `quick_ping_tab.py:73-75`, `widgets/history_dialog.py:85-87` | `border-radius` 5px vs 6px; `padding` varia |
| Botão primário (`#7c3aed` / hover `#6d28d9`) | `widgets/_utils.py:23-27` (`PRIMARY_BTN_STYLE`) | `quick_ping_tab.py:65-68` (`_PRIMARY_BTN`), `widgets/host_card.py:262-264` | `border-radius` 5px vs 6px; padding/font-weight diferentes do helper |
| Rótulo de campo (`#6b7280`, 10px, `letter-spacing:0.5px`) | `widgets/_utils.py:19` (`field_label()`) | `quick_ping_tab.py:29` (`_STAT_LABEL_STYLE`), `widgets/host_card.py:43,166` | idêntico byte-a-byte ao helper, só não importado |
| Label de status da sonda (`#6b7280`, 12px, `padding:2px 0`) | Não existe helper | 3x em `mtr_tab.py` (143, 235\*, 263), 3x em `traceroute_tab.py` (113, 188\*, 214) | idêntico entre as duas abas; `mtr_tab.py` e `traceroute_tab.py` claramente copiados um do outro (\* variante "em execução" usa `#a78bfa`) |

Esses 4 padrões cobrem a maior parte da duplicação de QSS inline entre abas. `scan_tab.py` e
`banner_tab.py` usam majoritariamente estilos únicos (labels `color:#9ca3af;` simples), sem
contraparte duplicada relevante em outros arquivos além do padrão de rótulo cinza já citado.

## Observações gerais para o redesign

- O sistema de tema via `palette()` (regra do `CLAUDE.md`) é respeitado para fundos/bordas de
  painéis — os hex hardcoded encontrados são majoritariamente cores **semânticas** (status, RTT,
  severidade), não cores de tema claro/escuro quebradas.
- Boa oportunidade de refatoração de baixo risco antes do redesign visual: mover as cores semânticas
  repetidas para constantes em `_utils.py` (ex.: `STATUS_COLORS`, `DANGER_BTN_STYLE`) e substituir as
  duplicações listadas acima por imports — reduz ~90 ocorrências sem mudar nenhum comportamento.
