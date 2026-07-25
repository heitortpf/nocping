# Verificação final — Fase 3 (redesign visual completo)

Verificação única de tudo que a Fase 3 implementou (3.1 Banner/TLS, 3.2
Traceroute, 3.3 Port Scan, 3.4 MTR, 3.5 Quick Ping, 3.6 Monitor, 3.7 sidebar
de navegação), usando o `take_shots.py` e o baseline já corrigidos nos
prompts anteriores. Não é um re-redesign — só confirmação + lista de
pendências pontuais, se houver.

## Metodologia

1. `take_shots.py` rodado no estado atual (branch com Fase 3 completa) →
   12 imagens em `docs/redesign/screenshots-post/{dark,light}/`.
2. Comparação lado a lado com `docs/baseline/screenshots-pre/` (10 imagens
   originais + `quick_ping.png` adicionado no Prompt 2) para as 6 seções,
   nos dois temas — estado vazio/idle.
3. Verificação adicional (além do que foi pedido, mas necessária pra
   confiança real): populei Quick Ping e Monitor com dados simulados
   (RTT, jitter, perda) pra conferir que os cálculos e cores continuam
   corretos depois de toda a integração da sidebar — screenshots em
   `docs/redesign/screenshots-post/` não incluem esses (foram só verificação
   visual ad-hoc, não fazem parte do conjunto de 12 pedido).
4. Redimensionamento: cada uma das 6 seções capturada em 850×550 (perto do
   mínimo da janela, 800×500) e 1400×850 (grande).
5. Tema, Ctrl+N, fechar: testados via script in-process que efetivamente
   troca tema, abre uma segunda `MainWindow`, e fecha ambas.
6. `pytest tests/ -v -m "not live"`.

## Resultado por seção

### Quick Ping — OK
Vazio e preenchido (RTT hero, 6 stat cards, console, gráfico) idênticos em
estrutura ao que foi validado no prompt da própria aba. Sem cortes/sobreposição
em 850×550 nem 1400×850, nos dois temas. Cores de status (verde RTT/média,
vermelho perda 12,5%) corretas.

### Monitor — OK, com um ajuste cosmético pontual
HostCard (hero RTT, média/jitter/perda, mini-gráfico) renderiza corretamente
com dados simulados; cor de perda (17%) corretamente vermelha (`>5%`).
**Achado:** em 850×550 (janela quase no mínimo), o botão "Limpar Todos" no
card de controles trunca pra **"Limpar Todo"** (falta o "s") — o texto não
tem elipse, só corta. Cosmético, um único caractere, só aparece perto do
tamanho mínimo da janela. Não é um bug de dados/lógica.

### Port Scan — precisa de ajuste
Estado vazio idêntico ao esperado nos dois temas, em 1100×700 e 1400×850.
**Achado real, mais sério que o do Monitor:** em 850×550 (perto do mínimo
800×500 que a janela já permite hoje), o card de controles tem 6 campos
(Host/Portas/Timeout/Threads/VersãoIP/Protocolo) + 3 chips de preset +
checkbox + 3 botões de ação numa estrutura que não quebra linha nem
comprime graciosamente — o resultado é texto **visivelmente cortado e
ilegível**: o botão "Iniciar Scan" vira "niciar S", "Exportar CSV" vira
"Exportar (", o chip "Todas (1-65535)" vira "→das (1-6553", e o checkbox
"UDP open|filtered" vira "UDP oper". Isso não é sobreposição nem crash — é
o layout ficando sem espaço e o Qt cortando texto de widgets sem redimensionar
ou quebrar linha. Diferente do Monitor (1 caractere, cosmético), aqui vários
elementos ficam ininteligíveis. **Recomendo voltar pro prompt do Port Scan**
especificamente pra tratar o card de controles em larguras pequenas (ex.:
permitir quebra de linha na `action_row`, ou dar `minimumWidth` aos botões
críticos em vez de deixar comprimir livre).

### Banner/TLS — OK
Idêntico ao esperado nos dois temas; sem cortes em 850×550 (só 4 campos no
card de controle, cabe com folga). "Cifra" (bug de contraste corrigido no
prompt da própria aba) continua legível no tema claro.

### Traceroute — OK
Aviso de admin, seção avançada, tabela com zebra — tudo conforme o esperado.
Sem cortes em 850×550.

### MTR — OK
Card compacto (Host/Versão IP + Avançado colapsado) cabe folgado até em
850×550; a tabela de 10 colunas ganha scroll horizontal nessa largura, o que
é o comportamento correto (não corta, não sobrepõe — só exige rolar).

## Testes automatizados

```
pytest tests/ -v -m "not live"
77 passed, 3 deselected
```

## Teste manual

- **Redimensionar**: todas as 6 seções testadas em 850×550 e 1400×850 —
  resultado documentado seção por seção acima. `_FlowLayout` do Monitor
  continua quebrando linha corretamente (não foi tocado nesta fase).
- **Alternar tema**: `_toggle_theme()` inverteu `_is_dark` corretamente e
  propagou pra todas as instâncias abertas.
- **Ctrl+N**: segunda `MainWindow` abre limpa na seção Quick Ping e herda o
  tema da primeira janela corretamente.
- **Fechar**: `closeEvent`/`_shutdown()` não foram tocados na Fase 3 — não
  re-testei o encerramento do processo aqui porque isso já foi verificado
  de ponta a ponta (processo real, `tasklist`) no prompt da sidebar (3.7).

## Lista objetiva

| Seção | Status | Motivo |
|---|---|---|
| Quick Ping | **OK** | — |
| Monitor | **OK** (ajuste cosmético opcional) | "Limpar Todos" trunca 1 caractere só perto do tamanho mínimo da janela — baixa prioridade |
| Port Scan | **PRECISA DE AJUSTE** | Card de controles corta texto de vários botões/chips a ponto de ficar ilegível em janelas perto do tamanho mínimo (850×550) — layout não comprime nem quebra linha |
| Banner/TLS | **OK** | — |
| Traceroute | **OK** | — |
| MTR | **OK** | — |

**Recomendação:** só Port Scan precisa voltar pro prompt daquela aba antes
da Fase 4 (tratar responsividade do card de controles em larguras pequenas).
O item do Monitor é opcional/cosmético — pode ser incluído no mesmo retrabalho
se for conveniente, mas não bloqueia sozinho.
