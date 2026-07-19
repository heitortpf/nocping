# Plano de Resolução: Notificações de Perda de Pacote

## Análise do Problema
O usuário relatou que, ao ocorrer uma perda de pacote (packet loss), a notificação não sobe corretamente.
Ao analisar a lógica no `HostCard` (`ui/widgets/host_card.py`) e `MainWindow` (`ui/main_window.py`), identificamos o seguinte comportamento:
1. Quando um único ping falha (perda de pacote), o `HostCard` imediatamente altera o status para `HostStatus.DOWN`.
2. A `MainWindow` detecta a mudança e emite a notificação de "Host offline" no System Tray, configurada para durar 4000ms.
3. Se o próximo ping (1 segundo depois) for bem-sucedido, o `HostCard` altera o status de volta para `HostStatus.UP`.
4. A `MainWindow` detecta a mudança e emite a notificação de "Host online" no System Tray, **sobrescrevendo instantaneamente** a notificação de falha que estava na tela há apenas 1 segundo.
5. Como resultado, o usuário não consegue visualizar a notificação de queda/perda de pacote.

## Solução Proposta

Existem duas abordagens principais para resolver esse problema (precisamos do feedback do usuário):

**Opção 1: Adicionar um limite de tempo (Debounce / Threshold) para o status**
- Em vez de mudar para `DOWN` no primeiro pacote perdido, o host só é considerado `DOWN` após N falhas consecutivas (ex: 3 pacotes perdidos em sequência).
- Se a intenção do usuário é ser alertado a cada pacote perdido individualmente, essa opção não é ideal. Mas é o padrão em ferramentas de monitoramento.

**Opção 2: Desacoplar a Notificação de Perda de Pacote (Recomendada)**
- Criar um novo tipo de notificação específica para "Perda de Pacote". 
- Se a perda de pacote ocorrer, mas o host não ficar offline de forma persistente, o sistema exibirá uma notificação de "Aviso de Perda de Pacote" (ex: Host teve falha de resposta, perda X%).
- Evitar exibir a notificação de "Host voltou ONLINE" se ele ficou DOWN por um tempo muito curto (ex: menos de 5 segundos), reduzindo o spam visual de notificações concorrentes.
- Além disso, implementar uma tolerância no status `DOWN`: mudar para uma notificação de `WARNING` ao perder um pacote isolado e só ir para `DOWN` real após múltiplas falhas.

## Alterações Necessárias

1. **`core/models.py`**:
   - Adicionar `HostStatus.WARNING` (ou `DEGRADED`) para representar o estado onde pacotes isolados estão sendo perdidos.

2. **`ui/widgets/host_card.py`**:
   - Adicionar controle de "falhas consecutivas" (consecutive_failures).
   - Se falhar 1 vez: altera o status para `WARNING`.
   - Se falhar > N vezes (ex: 3): altera para `DOWN`.
   - Se voltar a ter sucesso: altera para `UP` e zera as falhas.

3. **`ui/main_window.py`**:
   - Adicionar tratamento para o status `WARNING`, disparando uma notificação de aviso de Perda de Pacote ("Pacote perdido no host X").
   - Ajustar o fluxo de notificações para não sobrepor mensagens imediatamente de forma indesejada, possivelmente adicionando um pequeno delay ou dependendo das falhas consecutivas.
