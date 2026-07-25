# NOCPing — Design System

Documenta a camada de tokens/componentes criada em `ui/theme/` para centralizar
cores, espaçamento, raio de borda e tipografia do app. Ver contexto/motivação
em `docs/baseline/REPORT.md` (auditoria feita antes desta refatoração).

**Escopo desta etapa:** só a camada de estilo. Nenhuma aba teve sua lógica
alterada — `ui/main_window.py` e `ui/widgets/_utils.py` foram reescritos para
consumir `ui/theme/tokens.py` em vez de hex literais, mas geram exatamente o
mesmo QSS de antes (verificado por diff de pixels contra os screenshots de
`docs/baseline/`, ver seção "Verificação" abaixo). `ui/theme/components.py` é
o novo builder canônico para código futuro — as abas ainda não foram migradas
para ele.

## Estrutura

```
ui/theme/
  tokens.py       — ColorTokens (DARK/LIGHT), Spacing, Radius, Typography
  components.py   — primary_button, secondary_button, danger_button,
                     card_frame, section_label, status_badge
ui/widgets/_utils.py
                  — API legada (rtt_color, field_label, PRIMARY_BTN_STYLE,
                    TABLE_STYLE) agora implementada sobre ui/theme/*
```

Regra: nenhum módulo de UI deve declarar cor hex literal para elementos de
aplicação. Sempre importar de `ui.theme.tokens` (`DARK` / `LIGHT` /
`tokens_for(dark)`). Exceção aceita: QSS que usa `palette(...)` do Qt (já
segue o tema automaticamente e não precisa de token).

## Paleta

### Como ler

Cada tema (`DARK`, `LIGHT` em `tokens.py`) é uma instância de `ColorTokens`
com ~26 campos. Os que importam para quem for estilizar uma aba nova:

| Token | Uso | Escuro | Claro |
|---|---|---|---|
| `bg` | fundo da janela | `#11111b` | `#eff1f5` |
| `surface` | fundo de cards/inputs (Base) | `#181825` | `#ffffff` |
| `surface_elevated` | menus, abas inativas, trilho de scrollbar | `#1e1e2e` | `#e6e9ef` |
| `border` | bordas padrão, divisores | `#45475a` | `#bcc0cc` |
| `text_primary` | texto principal | `#cdd6f4` | `#4c4f69` |
| `text_secondary` | placeholder de campo | `#6b7280` | `#9ca3af` |

### Marca (mantida — roxo `#7c3aed`)

| Token | Valor | Uso |
|---|---|---|
| `primary` | `#7c3aed` | ação principal, foco de campo, aba selecionada |
| `primary_hover` | `#6d28d9` | hover de botão primário |
| `primary_press` | `#5b21b6` | pressed de botão primário |

Idêntico nos dois temas — é a cor de marca, não deve variar com o tema.

### Semânticas de status

| Token | Valor | Significado |
|---|---|---|
| `success` | `#4ade80` | host UP, RTT baixo, admin OK |
| `warning` | `#facc15` | ERROR de host, RTT médio, sem admin |
| `danger` | `#f87171` | host DOWN, RTT alto/timeout |
| `danger_strong` / `danger_strong_hover` | `#dc2626` / `#b91c1c` | botões destrutivos (Limpar, Remover) — mais saturado que `danger` porque é fundo sólido de botão, não texto sobre `surface` |
| `info` | `#a78bfa` | estado "em execução/iniciando" (host RUNNING, sonda em andamento) |

Também idênticas nos dois temas hoje. Ficam definidas por tema em
`ColorTokens` (não como constantes globais soltas) para permitir divergência
futura sem mudar a assinatura de nada que já consome os tokens.

### Tokens auxiliares (paridade com o legado, não "oficiais")

Ao extrair o QSS espalhado, apareceram valores que **não** se encaixam
limpo em `bg`/`surface`/`border` porque o código original já misturava
papéis do `QPalette` de forma inconsistente entre os dois temas. Em vez de
"corrigir" silenciosamente (o que mudaria pixels), esses valores viraram
campos próprios e documentados aqui:

- `field_bg` — fundo de `QLineEdit`/`QComboBox`. No escuro é igual a
  `button_bg`; no claro é igual a `surface`. Não são o mesmo conceito, só
  coincidem por tema.
- `button_bg` — papel `Button` do Qt (botões padrão, hover de item de menu).
- `control_bg` / `control_hover` / `control_press` — fundo/hover/pressed das
  setinhas do `QSpinBox`. No escuro usa o valor de `border`; no claro usa o
  de `button_bg`. Mesma observação acima.
- `pane_border` — borda do `QTabWidget::pane`. Escuro usa `button_bg`, claro
  usa `border`.
- `text_muted` — cinza fixo `#6b7280` usado em `field_label()`, barra de
  status e boa parte dos rótulos de status das abas — **invariante entre
  temas** (não muda com `PlaceholderText`, que é `text_secondary`).
- `tab_fg_inactive` — cinza fixo `#9ca3af` da aba não selecionada, também
  invariante entre temas.

**Dívida técnica identificada (não corrigida nesta etapa):** `text_muted` e
`text_secondary` deveriam provavelmente ser o mesmo conceito, mas hoje têm
valores diferentes no tema escuro (`#6b7280` vs `#6b7280` — coincidem) e no
claro (`#6b7280` vs `#9ca3af` — divergem). Fica registrado para quando as
abas forem migradas para `ui/theme/components.py`.

## Espaçamento

Escala de 4px (`Spacing` em `tokens.py`):

| Token | Valor |
|---|---|
| `xs` | 4px |
| `sm` | 8px |
| `md` | 12px |
| `lg` | 16px |
| `xl` | 24px |
| `xxl` | 32px |

Uso pretendido: `xs`/`sm` para gaps internos de linha (labels ↔ valores),
`md`/`lg` para padding de botões e margens de painel, `xl`/`xxl` para
espaçamento entre seções maiores (ex.: entre o painel de controles e a área
de resultados de uma aba).

## Raio de borda

| Token | Valor | Uso pretendido |
|---|---|---|
| `sm` | 6px | botões, inputs |
| `md` | 10px | cards (`card_frame()` usa este como padrão — é o raio já usado em `HostCard`) |
| `lg` | 16px | painéis grandes/modais, se necessário |

## Tipografia

`Typography` em `tokens.py` define 4 estilos (`TypeStyle(size, weight)`,
`weight` no formato numérico do `QFont.Weight`):

| Estilo | Tamanho | Peso | Uso |
|---|---|---|---|
| `tab_title` | 14px | 700 (bold) | título de aba/seção — usado por `section_label()` |
| `label` | 10px | 500 | rótulo pequeno de campo (ex.: "HOST / IP") — usado por `field_label()` |
| `value` | 18px | 700 (bold) | valor em destaque (ex.: RTT atual, contador) |
| `body` | 12px | 400 (normal) | texto de corpo, tabelas, log |

Só `tab_title` e `label` estão conectados a builders reais hoje
(`section_label()`, `field_label()`). `value` e `body` documentam o padrão
observado nas abas (ex.: `_val_rtt` no Quick Ping usa 18px/bold) para quando
essas telas forem migradas para os builders — hoje cada aba ainda declara o
tamanho inline.

## Componentes (`ui/theme/components.py`)

Builders novos, ainda não usados pelas abas (ver "Escopo desta etapa"
acima). Cada um retorna um widget Qt pronto, já com `setStyleSheet()`
aplicado:

- `primary_button(text, icon=None)` — substitui `PRIMARY_BTN_STYLE`.
- `secondary_button(text, icon=None)` — botão neutro que segue o tema via
  `palette()`; formaliza o padrão que hoje é reescrito inline em
  `monitor_tab.py`, `scan_tab.py`, `quick_ping_tab.py` etc. (`background:
  palette(button); ... hover: palette(mid)`).
- `danger_button(text, icon=None)` — novo: antes de existir, cada aba
  reimplementava o botão vermelho (`#dc2626`/`#b91c1c`) na mão em pelo menos
  3 arquivos (ver `docs/baseline/REPORT.md`, seção 4).
- `card_frame(radius=RADIUS.md)` — painel `background: palette(base); border:
  1px solid palette(mid); border-radius: Npx`, o padrão repetido em
  `HostCard`, nos painéis do Quick Ping, Monitor, Traceroute e MTR.
- `section_label(text)` — título de seção usando `TYPOGRAPHY.tab_title`.
- `status_badge(status: HostStatus)` — label colorida com o texto padrão do
  status (INATIVO/INICIANDO…/ONLINE/OFFLINE/ERRO), mesma semântica que
  `STATUS_COLOR`/`STATUS_LABEL` hoje duplicados em `host_card.py`.

`icon` (nos builders acima) é uma string (emoji), seguindo a convenção já
usada no app (`"▶  Iniciar"`, `"🗑  Limpar histórico"`) — os builders em si
**não foram alterados** para aceitar `QIcon`.

## Ícones — decisão: qtawesome (a partir do redesign do Banner/TLS)

A partir da aba Banner/TLS, ícones de emoji foram substituídos por
`qtawesome` (`ui/banner_tab.py`) em vez de emoji ou SVG próprio:

- **Por quê:** ícones vetoriais consistentes entre plataformas (emoji renderiza
  diferente por SO/fonte do sistema), sem precisar curar/gerenciar arquivos
  `.svg` como asset; empacota bem com PyInstaller (fonte de ícones embutida
  no pacote `qtawesome`).
- **Dependência:** `qtawesome` adicionado a `requirements.txt` (traz `qtpy`
  como dependência transitiva).
- **Uso:** `qtawesome.icon(nome, color=hex)` retorna um `QIcon` — aplicado via
  `QPushButton.setIcon(...)` ou renderizado como `QPixmap` num `QLabel` para
  cabeçalhos de seção. **Não** foi integrado ao parâmetro `icon=` dos builders
  de `ui/theme/components.py` (que continuam esperando string/emoji) — isso
  ficou fora do escopo do redesign do Banner/TLS; se/quando os builders forem
  migrados para aceitar `QIcon`, atualizar este documento.
- **Cor dos ícones:** só usar tokens **invariantes entre temas**
  (`primary`, `success`, `warning`, `danger`, `info`, `on_primary`) para
  colorir ícones. `qtawesome.icon()` "queima" a cor no momento da criação —
  não há re-tintagem automática ao trocar de tema como acontece com
  `palette()` em QSS. Se algum dia for necessário um ícone na cor de texto
  (`text_primary`/`text_secondary`, que MUDA por tema), ele precisará ser
  recriado no `_toggle_theme()` do `MainWindow` — nenhuma aba faz isso hoje.
- **Migração:** as demais abas (Quick Ping, Monitor, Port Scan, Traceroute,
  MTR) ainda usam emoji — não foram tocadas nesta etapa. Trocá-las é uma
  decisão própria, não implícita nesta.

### `PRIMARY_BTN_QSS` / `SECONDARY_BTN_QSS` / `DANGER_BTN_QSS`

Os builders aplicam QSS pré-computado como **strings de módulo**, não
construído instanciando um `QPushButton` real na importação — isso importa
porque `ui/widgets/_utils.py` importa `PRIMARY_BTN_QSS` no nível de módulo, e
qualquer coisa que crie um `QWidget` antes de existir uma `QApplication`
derruba o processo. (Foi exatamente esse bug que quebrou a primeira versão
desta refatoração — ver commit desta etapa.)

## Regras de uso

1. **Cor hex literal em `ui/*.py` = proibido**, exceto dentro de
   `ui/theme/tokens.py`. Se precisar de uma cor, importe o token; se o token
   não existir, adicione em `tokens.py` (não hardcode).
2. **`palette(...)` continua válido** para tudo que já segue o tema
   automaticamente — não precisa virar token só para existir.
3. Ao criar uma tela nova, prefira os builders de `ui/theme/components.py` a
   montar QSS inline. Se o builder não cobrir o caso, é sinal de que falta
   um builder — adicionar um novo, não voltar a escrever QSS solto na aba.
4. `ui/widgets/_utils.py` continua existindo por compatibilidade
   (`rtt_color`, `field_label`, `PRIMARY_BTN_STYLE`, `TABLE_STYLE` — todas as
   abas atuais importam daqui). Não adicionar funcionalidade nova ali; código
   novo vai direto em `ui/theme/`.

## Verificação

- `pytest tests/ -v -m "not live"` — 77 passed, 3 deselected (mesmo
  resultado de antes da refatoração, ver `docs/baseline/tests-pre-redesign.txt`).
- Diff de pixels entre `docs/baseline/screenshots-pre/{dark,light}/*.png` e
  screenshots pós-refatoração das mesmas 5 abas/2 temas: 8/10 idênticos byte
  a byte; os outros 2 (`monitor.png`, ambos os temas) diferem em 4 pixels
  isolados na borda de um mini-gráfico de RTT — antialiasing entre duas
  renderizações separadas do pyqtgraph, não mudança de cor sistemática (os
  demais milhões de pixels da mesma imagem são idênticos).

## Próximos passos (fora do escopo desta etapa)

- Migrar cada aba para os builders de `ui/theme/components.py` (começar por
  `monitor_tab.py`/`host_card.py`, que têm a maior concentração de QSS
  duplicado segundo `docs/baseline/REPORT.md`).
- Resolver a divergência `text_muted` vs `text_secondary` apontada acima.
- Depois de todas as abas migradas, `ui/widgets/_utils.py` pode ser
  removido e suas importações trocadas por `ui.theme.tokens`/`ui.theme.components`
  diretamente.
