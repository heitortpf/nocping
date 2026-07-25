# Checklist manual de QA — release v2.0.0

Checklist para validação manual antes de taguear `v2.0.0`. Cobre o que a
suíte automatizada (`pytest tests/ -v -m "not live"`, 110 testes) **não**
cobre: privilégios de admin/root reais, comportamento de instalador/
Gatekeeper, e feedback visual/sensorial (bandeja do sistema, redimensionamento
ao vivo) que só um humano consegue julgar com confiança.

Não repete o que já foi verificado e documentado em sessões anteriores
(`docs/redesign/VERIFICACAO_FASE3.md`, `docs/PERFORMANCE.md`) — assume que
quem for rodar isso já leu o changelog da v2.0.0 no `README.md` pra saber o
que mudou.

**Como usar:** marque cada item com `[x]` conforme testa. Se algo falhar,
anote o problema numa linha `> ⚠` logo abaixo do item, não apague o checkbox
não marcado. Ao final, preencha a seção "Resultado" com aprovado/reprovado
por plataforma.

---

## Status desta rodada (automação, Windows sem admin)

O ambiente onde este checklist foi escrito é Windows sem privilégios
elevados, sem Linux/macOS disponíveis. Nesta rodada, automatizei tudo que
dava pra verificar programaticamente daqui — via `MainWindow` real (não
mockada) dirigida por script, com screenshots e captura de sinais reais
como evidência — e deixei os checkboxes abaixo **sem marcar**, porque são
pra validação humana; o que segue é só o resumo do que a automação já
cobriu, pra quem for rodar manualmente saber o que pode revisar mais rápido
e o que ainda não foi tocado.

**Cobertos com evidência em `docs/redesign/qa_v2_evidence/`:**
- Seção 1 (Windows sem Administrador): todos os 8 itens aplicáveis a "sem
  admin" passaram — TCP funciona, ICMP vira ERROR sem crashar, Port Scan
  TCP/UDP completa, Traceroute/MTR avisam corretamente.
- Seção 4 (redimensionamento): 12 screenshots (6 abas × 800×500/1400×900)
  em `qa_v2_evidence/resize/` — sem corte/sobreposição de texto em nenhuma.
- Seção 5 (Ctrl+N): abre segunda janela em Quick Ping, tema herdado,
  monitoramento independente entre janelas, alternar tema propaga, **e o
  achado de fechar-janela-secundária-derruba-tudo já foi corrigido** (ver
  abaixo).
- Seção 6 (exportação): as 8 exportações aplicáveis (Quick Ping CSV, Monitor
  CSV+JSON, HostCard "Exportar RTT", Histórico CSV, Port Scan CSV,
  Traceroute CSV, MTR CSV) geram arquivo com conteúdo correto —
  Traceroute/MTR testados com dados sintéticos na tabela (sem admin não há
  hop real pra popular).
- Seção 7 (tema): propagação testada via automação (`tests/test_ui_theme.py`,
  8 testes) + inspeção visual das 12 imagens em `screenshots/{dark,light}/`.
- Seção 8 (notificações): DOWN/UP-após-DOWN/ERROR testados no Monitor
  (captura real de `showMessage`, não só inspeção visual), toggle
  desliga/religa corretamente, preferência persiste via `QSettings` — **mas
  ver achado abaixo sobre Quick Ping**.

**Dois achados reais durante esta rodada** (não são itens que "passaram
com ressalva" — são comportamento confirmado, precisam de uma decisão):

1. ~~**Fechar a janela secundária derruba o app inteiro.**~~ **CORRIGIDO.**
   `MainWindow.closeEvent()` chamava `QApplication.quit()`
   incondicionalmente, em qualquer instância — confirmado com um
   `app.exec()` real (não só `processEvents()`), então não era artefato do
   jeito de testar. Era anterior a esta sessão de redesign (`git log -p`
   mostrava o método assim há várias releases). Corrigido: `closeEvent()`
   agora limpa os workers da própria janela, sai de `_instances`, esconde
   o próprio ícone de bandeja, e só chama `quit()` se `_instances` ficar
   vazia. `_shutdown()` (via `aboutToQuit`) continua cobrindo os atalhos
   que pulam `closeEvent()` (menu "Sair", bandeja "Sair"). Validado com
   `app.exec()` real de novo (processo externo, PID monitorado via
   PowerShell) + `tests/test_multi_window_close.py` (10 testes). Ver
   Seção 5.
2. **Quick Ping não notifica em ERROR, só em DOWN/UP.** `QuickPingTab._on_error()`
   (disparado por ICMP/UDP sem admin, ou qualquer falha antes do primeiro
   resultado) não emite `host_status_changed` — só `_on_result()` faz isso,
   e só a partir da segunda mudança de status observada. O changelog da
   v1.5.0 no README já falava só em "UP/DOWN" pra Quick Ping (não ERROR),
   então isto pode ser escopo intencional, não bug — mas o item original
   deste checklist assumia paridade total com o Monitor, o que estava
   errado. Ver item corrigido na Seção 8.

**Não coberto nesta rodada — precisa de humano e/ou outra plataforma:**
Windows COM admin (precisa elevação interativa via UAC), toda a Seção 2
(Linux), toda a Seção 3 (macOS/Gatekeeper), e o julgamento visual de "a
notificação realmente aparece na tela e não é picotada/atrasada" (a
automação capturou a *chamada* de `showMessage()`, não a renderização real
do toast do SO).

---

## 0. Preparação

- [ ] `pip install -r requirements.txt` roda sem erro no ambiente de teste
- [ ] `pytest tests/ -v -m "not live"` passa 100% localmente antes de começar
      o manual (se não passar, pare — não faz sentido validar manualmente
      uma build que já falha no automatizado)
- [ ] Build gerado via PyInstaller (não `python main.py`) — o QA final deve
      ser no executável que vai ser publicado, não no código-fonte direto:
      `python -m PyInstaller --onefile --windowed --name NOCPing --icon NOCPing.ico --add-data "NOCPing.ico:." main.py`

---

## 1. Windows

### 1.1 Com Administrador
- [ ] Clique direito no `.exe` → "Executar como administrador"
- [ ] Barra de status mostra "🔐 Admin" (não "⚠ Sem Admin")
- [ ] Monitor: adicionar host em modo **ICMP** — pinga normalmente, sem erro
- [ ] Monitor: adicionar host em modo **UDP** — pinga normalmente, sem erro
- [ ] Quick Ping: modo ICMP e UDP funcionam (mesmo teste acima, aba diferente)
- [ ] Traceroute: roda sem o aviso de admin, tabela popula hop a hop
- [ ] MTR: roda sem o aviso de admin, estatísticas por hop acumulam continuamente
- [ ] Rodar **Monitor (ICMP) + Quick Ping (ICMP) + MTR** simultaneamente por
      ~1 minuto — conferir que RTT/perda de uma aba não vaza pra outra
      (regressão específica corrigida na v1.4.0 — DPI + PID por thread,
      ver `CLAUDE.md`)

### 1.2 Sem Administrador
**Verificado via automação nesta rodada (todos os 8 itens abaixo) —
`python main.py`/código-fonte, não o `.exe` empacotado; recomendável repetir
uma vez no `.exe` real antes de assinar como aprovado.**
- [x] Abrir o `.exe` normalmente (duplo clique, sem "Executar como administrador")
- [x] Barra de status mostra "⚠ Sem Admin (ICMP/UDP indisponível)"
- [x] Monitor: adicionar host em modo **TCP** — funciona normalmente
- [x] Monitor: adicionar host em modo **ICMP** — falha com mensagem de erro
      clara (card fica em estado ERROR, não trava nem crasha o app)
- [x] Port Scan: scan TCP funciona sem erro nem prompt de privilégio
- [x] Port Scan: scan UDP funciona sem erro nem prompt de privilégio
      (Port Scan não precisa de admin em nenhum protocolo — só
      Monitor/Quick Ping em modo ICMP/UDP e Traceroute/MTR precisam)
- [x] Traceroute: exibe aviso "requer Administrador", não trava o app
- [x] MTR: exibe aviso "requer Administrador", não trava o app
- [x] Banner/TLS: funciona normalmente (é TCP puro)

---

## 2. Linux

### 2.1 Com root (`sudo ./NOCPing-Linux`)
- [ ] Barra de status mostra "🔐 Admin"
- [ ] Monitor/Quick Ping em modo ICMP e UDP funcionam
- [ ] Traceroute e MTR funcionam (raw socket ICMP liberado)

### 2.2 Sem root (`./NOCPing-Linux`)
- [ ] Barra de status mostra "⚠ Sem Admin"
- [ ] Monitor/Quick Ping em modo TCP funcionam
- [ ] Monitor/Quick Ping em modo ICMP falha graciosamente (sem crash)
- [ ] Port Scan TCP/UDP funciona normalmente (não depende de root)
- [ ] Traceroute/MTR mostram aviso de privilégio, não travam

### 2.3 Ambiente gráfico
- [ ] App abre normalmente em pelo menos uma distro com X11 (ex.: Ubuntu/Debian)
- [ ] Se possível, testar também sob Wayland — anotar qualquer glitch visual
      (tema, ícone da bandeja, redimensionamento) já que o CI só valida
      Linux via `xvfb` (offscreen, sem compositor real)
- [ ] Ícone da bandeja do sistema aparece e responde a duplo-clique

---

## 3. macOS

### 3.1 Gatekeeper (primeira execução)
- [ ] Baixar `NOCPing-macOS`, dar `chmod +x`, tentar abrir com duplo-clique
      **sem** rodar `xattr -cr` antes — confirmar que o Gatekeeper bloqueia
      com o aviso padrão de "desenvolvedor não identificado" (comportamento
      esperado, não é bug)
- [ ] Rodar `xattr -cr NOCPing-macOS` e abrir de novo — deve abrir normalmente
- [ ] Ícone da aplicação aparece corretamente no Dock (checar conversão
      `.ico` → `.icns` via Pillow no build, mencionada no `CLAUDE.md`)

### 3.2 Com/sem sudo
- [ ] Sem `sudo`: barra de status "⚠ Sem Admin"; TCP funciona, ICMP/UDP falha
      graciosamente; Traceroute/MTR mostram aviso
- [ ] Com `sudo ./NOCPing-macOS`: barra de status "🔐 Admin"; ICMP/UDP/
      Traceroute/MTR funcionam

---

## 4. Redimensionamento de janela (todas as 6 abas)

Janela mínima é 800×500 (`setMinimumSize`). Testar em cada uma das 6 seções
(sidebar): **Quick Ping, Monitor, Port Scan, Banner/TLS, Traceroute, MTR**.

Para cada aba (verificado via automação nesta rodada — 12 screenshots em
`docs/redesign/qa_v2_evidence/resize/`, incluindo Monitor com 3 hosts
ativos e grade de cards sob pressão):
- [x] Redimensionar pra ~800×500 (mínimo) — nenhum texto de botão/label
      corta/sobrepõe (Port Scan e Monitor tiveram esse bug corrigido via
      `ReflowRow` nesta fase — ver `docs/redesign/VERIFICACAO_FASE3.md` —
      confirmado que continua corrigido na build final)
- [x] Redimensionar pra ~1400×900 (grande) — layout não fica com espaço
      vazio estranho nem widgets esticados de forma quebrada
- [ ] Redimensionar a janela **enquanto uma operação está rodando** (scan em
      andamento, MTR contínuo, monitor com hosts ativos) — sem travar/piscar
      (não testado com um scan/MTR realmente em andamento durante o próprio
      resize, só com Monitor populado; recomendo um teste manual rápido)
- [ ] MTR especificamente: em 850×550 a tabela de 10 colunas deve ganhar
      scroll horizontal (não cortar/sobrepor colunas)

---

## 5. Multi-janela (Ctrl+N)

Verificado via automação nesta rodada (`Ctrl+N` disparado de verdade via
`QTest.keyClick`, não chamando o método interno direto):
- [x] `Ctrl+N` na janela principal abre uma segunda `MainWindow`
- [x] A segunda janela abre limpa, na seção **Quick Ping**, com o mesmo tema
      da primeira
- [x] Iniciar monitoramento de hosts diferentes em cada janela — não
      interferem entre si (RTT/perda não cruzam entre janelas)
- [x] Alternar tema em uma janela (botão 🌙/☀ na barra de menu) — a outra
      janela também muda de tema junto
- [x] **CORRIGIDO — Fechar a janela SECUNDÁRIA (X) não encerra mais o app
      todo.** `MainWindow.closeEvent()` agora limpa os workers só daquela
      janela (`_cleanup_window()`, idempotente), sai de `_instances`,
      esconde o próprio ícone de bandeja, e só chama `QApplication.quit()`
      se `_instances` ficar vazia — ou seja, só na ÚLTIMA janela. Validado
      com `app.exec()` real duas vezes: uma vez dentro do processo de teste
      (janela 1 continua com host ativo — status `RUNNING` — depois de
      fechar a janela 2) e uma vez com um processo Python externo de
      verdade lançado via PowerShell, PID monitorado de fora — o log do
      processo prova que o loop de eventos continuou vivo e processando
      timers ~4s depois de fechar a secundária, só encerrando de fato ao
      fechar a última janela. Também coberto por
      `tests/test_multi_window_close.py` (10 testes).
- [x] Fechar a janela principal com a secundária ainda aberta — **agora
      só fecha aquela janela também** (não é mais "o processo inteiro
      encerra" nesse caso — só encerra quando é a ÚLTIMA janela restante,
      seja ela qual for). Nenhuma janela/ícone de bandeja fica órfã —
      `_tray.hide()` roda pra cada janela fechada, e `_shutdown()` (via
      `aboutToQuit`) limpa qualquer janela que ainda esteja em `_instances`
      quando o app realmente encerra (cobre os atalhos "Sair" do menu/
      bandeja, que chamam `QApplication.quit()` direto sem passar por
      `closeEvent()` janela por janela).

---

## 6. Exportação CSV/JSON por aba

| Aba | Exportação disponível |
|---|---|
| Quick Ping | Exportar CSV (histórico da sessão de ping atual) |
| Monitor | Exportar CSV **e** JSON (todos os hosts); "⬇ Exportar RTT" por host individual; "⏱ Histórico" → "⬇ Exportar CSV" (histórico SQLite do host) |
| Port Scan | Exportar CSV (portas encontradas) |
| Banner/TLS | **Não aplicável** — sem botão de exportação |
| Traceroute | Exportar CSV (hops) |
| MTR | Exportar CSV (estatísticas por hop) |

Para cada exportação da tabela acima (verificado via automação nesta
rodada para as 7 exportações aplicáveis — arquivos gerados em
`docs/redesign/qa_v2_evidence/exports/`; Traceroute/MTR com dados
sintéticos na tabela, já que raw socket ICMP não roda sem admin):
- [x] Gerar algum resultado na aba primeiro (não exportar tabela vazia sem
      querer testar esse caso separadamente)
- [x] Clicar exportar, escolher um caminho, confirmar que o arquivo é criado
- [x] Abrir o CSV/JSON gerado num editor de texto/planilha — cabeçalho e
      dados fazem sentido, sem campos truncados/corrompidos
- [ ] Testar exportar com resultado vazio (ex.: Port Scan sem nenhuma porta
      aberta) — não deve travar nem gerar arquivo corrompido/vazio-com-erro
      (não testado nesta rodada)
- [x] Monitor: exportar CSV/JSON com múltiplos hosts (misturei TCP + hosts
      persistidos de sessão anterior, um UP e um DOWN) — todos aparecem no
      JSON, inclusive os IDLE nunca iniciados

---

## 7. Alternância de tema

- [x] Botão 🌙/☀ na barra de menu alterna claro↔escuro sem travar
      (`tests/test_ui_theme.py`, 8 testes automatizados + verificado de novo
      manualmente nesta rodada com um `HostCard` real)
- [x] Testar a alternância em cada uma das 6 abas (não só na que abriu por
      padrão) — cores de texto/painéis acompanham o tema em todas
      (inspeção visual das 12 imagens em `screenshots/{dark,light}/`)
- [x] Testar com Monitor populado com hosts ativos (RTT variando ao vivo) —
      o mini-gráfico de RTT de cada card também troca de cor de fundo/eixo
      (não fica com fundo do tema antigo) — `test_toggle_theme_updates_monitor_host_card_graph`
- [ ] Fechar e reabrir o app — o tema detectado automaticamente
      (`darkdetect`) bate com o tema do SO (não testado — depende do tema
      real do SO no momento do teste, melhor feito manualmente)
- [ ] Se o SO permitir alternar tema do sistema em tempo real (Windows
      10/11), trocar o tema do SO **com o NOCPing já aberto** e conferir se
      o app reflete isso (comportamento esperado: só na próxima abertura,
      já que a detecção é feita na construção da janela — não é um bug se
      não atualizar ao vivo, mas vale confirmar que também não quebra nada)

---

## 8. Notificações de bandeja (UP / DOWN / ERROR)

Pré-requisito: `Visualizar → Notificações de host` marcado (é o padrão).

- [x] **DOWN** (Monitor): verificado via automação — TCP contra porta fechada
      dispara `showMessage()` com "offline" no título. Falta confirmar
      visualmente que o toast do SO realmente aparece (a automação só prova
      que a chamada acontece).
- [x] **UP após DOWN** (Monitor): verificado via automação — só notifica na
      transição DOWN→UP, não em todo ping bem-sucedido.
- [x] **ERROR** (Monitor): verificado via automação — host ICMP sem admin
      dispara `showMessage()` com "Erro" no título.
- [ ] **Quick Ping — DOWN/UP**: verificado via automação, funciona (mesma
      lógica do Monitor, só que exige uma transição de status real — a
      *primeira* leitura nunca notifica, só vira a linha de base).
- [ ] **Quick Ping — ERROR não notifica (achado, não item a "passar").**
      `_on_error()` do Quick Ping (ICMP/UDP sem admin, ou qualquer falha
      antes do 1º resultado) não emite `host_status_changed` — confirmado
      via automação (mock de `showMessage`, zero chamadas). O changelog da
      v1.5.0 já falava só "UP/DOWN" pra Quick Ping, então isso pode ser
      escopo intencional — mas se o comportamento esperado for paridade
      total com o Monitor (que trata ERROR explicitamente), isto é um gap
      a decidir se entra na v2.0.0.
- [ ] Desmarcar `Visualizar → Notificações de host` e repetir os cenários
      acima — nenhuma notificação aparece (verificado via automação pro
      Monitor; toggle + persistência via `QSettings` confirmados)
- [ ] Remarcar a opção, reabrir o app — a preferência persistiu
      (`QSettings`, chave `notifications_enabled`)
- [ ] Duplo-clique no ícone da bandeja restaura a janela principal se
      minimizada

---

## Resultado

| Plataforma | Build testado | Aprovado? | Observações |
|---|---|---|---|
| Windows 10/11 | | ☐ Sim ☐ Não | |
| Linux (distro: ____) | | ☐ Sim ☐ Não | |
| macOS (versão: ____) | | ☐ Sim ☐ Não | |

**Assinatura / responsável pelo QA:** ______________________
**Data:** ______________________

Se todas as três plataformas estiverem aprovadas, a tag `v2.0.0` pode ser
criada (`git tag v2.0.0 && git push origin v2.0.0`) — isso dispara o
workflow `.github/workflows/build.yml`, que agora só builda/publica se o
job `test` (pytest + pytest-qt) passar primeiro.
