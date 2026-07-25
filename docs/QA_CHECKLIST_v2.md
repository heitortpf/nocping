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
- [ ] Abrir o `.exe` normalmente (duplo clique, sem "Executar como administrador")
- [ ] Barra de status mostra "⚠ Sem Admin (ICMP/UDP indisponível)"
- [ ] Monitor: adicionar host em modo **TCP** — funciona normalmente
- [ ] Monitor: adicionar host em modo **ICMP** — falha com mensagem de erro
      clara (card fica em estado ERROR, não trava nem crasha o app)
- [ ] Port Scan: scan TCP funciona sem erro nem prompt de privilégio
- [ ] Port Scan: scan UDP funciona sem erro nem prompt de privilégio
      (Port Scan não precisa de admin em nenhum protocolo — só
      Monitor/Quick Ping em modo ICMP/UDP e Traceroute/MTR precisam)
- [ ] Traceroute: exibe aviso "requer Administrador", não trava o app
- [ ] MTR: exibe aviso "requer Administrador", não trava o app
- [ ] Banner/TLS: funciona normalmente (é TCP puro)

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

Para cada aba:
- [ ] Redimensionar pra ~800×500 (mínimo) — nenhum texto de botão/label
      corta/sobrepõe (Port Scan e Monitor tiveram esse bug corrigido via
      `ReflowRow` nesta fase — ver `docs/redesign/VERIFICACAO_FASE3.md` —
      confirmar que continua corrigido na build final)
- [ ] Redimensionar pra ~1400×900 (grande) — layout não fica com espaço
      vazio estranho nem widgets esticados de forma quebrada
- [ ] Redimensionar a janela **enquanto uma operação está rodando** (scan em
      andamento, MTR contínuo, monitor com hosts ativos) — sem travar/piscar
- [ ] MTR especificamente: em 850×550 a tabela de 10 colunas deve ganhar
      scroll horizontal (não cortar/sobrepor colunas)

---

## 5. Multi-janela (Ctrl+N)

- [ ] `Ctrl+N` na janela principal abre uma segunda `MainWindow`
- [ ] A segunda janela abre limpa, na seção **Quick Ping**, com o mesmo tema
      da primeira
- [ ] Iniciar monitoramento de hosts diferentes em cada janela — não
      interferem entre si (RTT/perda não cruzam entre janelas)
- [ ] Alternar tema em uma janela (botão 🌙/☀ na barra de menu) — a outra
      janela também muda de tema junto
- [ ] Fechar a janela secundária (X ou `Ctrl+Q`) — a principal continua
      funcionando normalmente
- [ ] Fechar a janela principal com a secundária ainda aberta — **o
      processo inteiro encerra** (não é "minimizar pra bandeja"; é
      comportamento intencional desde a v1.2.0, ver `CLAUDE.md`) e nenhuma
      janela/ícone de bandeja fica órfã no sistema depois

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

Para cada exportação da tabela acima:
- [ ] Gerar algum resultado na aba primeiro (não exportar tabela vazia sem
      querer testar esse caso separadamente)
- [ ] Clicar exportar, escolher um caminho, confirmar que o arquivo é criado
- [ ] Abrir o CSV/JSON gerado num editor de texto/planilha — cabeçalho e
      dados fazem sentido, sem campos truncados/corrompidos
- [ ] Testar exportar com resultado vazio (ex.: Port Scan sem nenhuma porta
      aberta) — não deve travar nem gerar arquivo corrompido/vazio-com-erro
- [ ] Monitor: exportar CSV/JSON com múltiplos hosts (misturar TCP/ICMP/UDP,
      alguns UP e alguns DOWN) — todos os hosts aparecem no arquivo

---

## 7. Alternância de tema

- [ ] Botão 🌙/☀ na barra de menu alterna claro↔escuro sem travar
- [ ] Testar a alternância em cada uma das 6 abas (não só na que abriu por
      padrão) — cores de texto/painéis acompanham o tema em todas
- [ ] Testar com Monitor populado com hosts ativos (RTT variando ao vivo) —
      o mini-gráfico de RTT de cada card também troca de cor de fundo/eixo
      (não fica com fundo do tema antigo)
- [ ] Fechar e reabrir o app — o tema detectado automaticamente
      (`darkdetect`) bate com o tema do SO
- [ ] Se o SO permitir alternar tema do sistema em tempo real (Windows
      10/11), trocar o tema do SO **com o NOCPing já aberto** e conferir se
      o app reflete isso (comportamento esperado: só na próxima abertura,
      já que a detecção é feita na construção da janela — não é um bug se
      não atualizar ao vivo, mas vale confirmar que também não quebra nada)

---

## 8. Notificações de bandeja (UP / DOWN / ERROR)

Pré-requisito: `Visualizar → Notificações de host` marcado (é o padrão).

- [ ] **DOWN**: no Monitor, adicionar um host que vai falhar (ex.: IP
      inexistente em modo TCP numa porta fechada, ou host realmente
      offline) — notificação "Host offline" aparece na bandeja
- [ ] **UP**: adicionar um host que responde, deixar cair propositalmente
      (ex.: desconectar a rede um instante) e voltar — notificação "Host
      online" aparece só quando volta de um estado DOWN anterior (não em
      todo ping bem-sucedido)
- [ ] **ERROR**: forçar um estado de erro (ex.: host inválido/não resolvível
      em modo ICMP sem admin) — notificação "Erro no Host" aparece
- [ ] Repetir DOWN/UP/ERROR a partir da aba **Quick Ping** (não só Monitor)
      — desde a v1.5.0 ela também emite essas notificações
- [ ] Desmarcar `Visualizar → Notificações de host` e repetir os 3 cenários
      acima — nenhuma notificação aparece
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
