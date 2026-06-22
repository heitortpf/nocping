# Plano de Refatoração e Otimização de Performance

Este documento detalha o plano de ação para tornar o NOCPing 100% rápido, escalável e com UI ultra-responsiva, resolvendo gargalos na arquitetura multithreading e no banco de dados.

## 🔴 User Review Required

> [!IMPORTANT]
> **Mudança de Paradigma no Monitor:** A troca de `QThread` (1 thread por host) para um `ThreadPoolExecutor` centralizado ou multiplexação de sockets alterará o núcleo do app. Isso melhorará drasticamente o consumo de CPU/RAM. Precisamos da sua aprovação antes de aplicar esta mudança arquitetural severa.

## ❓ Open Questions

> [!WARNING]
> 1. Você tem algum limite de hosts que espera monitorar simultaneamente na aba Monitor? (ex: 50, 500, 1000+)
> 2. O RTT Graph nas abas de Monitor deve atualizar em tempo real a cada ping, ou prefere que a interface atualize em "lotes" a cada 1 segundo para poupar a CPU quando houver 100+ hosts?

---

## 🛠️ Proposed Changes

### Core Network & Workers (Backend)
O principal gargalo atual é a explosão de threads. O `PingWorker` herda de `QThread`, o que significa que 100 hosts = 100 threads pesadas ativas na memória.

#### [MODIFY] `core/workers.py`
- Refatorar a emissão de sinais para evitar saturar o event loop principal. Se o usuário quiser 500 hosts, não podemos criar 500 QThreads. A longo prazo seria ideal usar um ThreadPool global, mas como otimização imediata sem reescrever todo o app, podemos garantir que as threads apenas durmam e usem sockets limpos, sem instanciar pesados timers de UI para cada uma.

#### [MODIFY] `core/history_store.py`
- **Gargalo:** Concorrência no SQLite pelo `_rw_lock` a cada ping.
- Mover a persistência para uma Fila Assíncrona / Dedicada. As threads de ping vão apenas colocar os resultados num objeto `queue.Queue()`, e um único timer ou thread de fundo vai fazer o `INSERT` no SQLite em lotes. Isso remove o bloqueio de IO das threads.

---

### Interface Gráfica (Frontend)
Quando muitos `pyqtgraph` estão visíveis, desenhá-los ao mesmo tempo mata a fluidez (60 FPS) da aplicação.

#### [MODIFY] `ui/widgets/rtt_graph.py`
- Adicionar limitação de taxa de atualização (Throttle). O `_redraw()` será disparado por um `QTimer` global ou rate-limiter, ao invés de recalcular a cada única inserção.
- Otimizar os arrays internos para usar numpy se aplicável, ou simplesmente travar os updates se a aba atual não estiver visível.

#### [MODIFY] `ui/monitor_tab.py`
- Pausar as atualizações dos gráficos (`HostCard`) quando a janela estiver minimizada ou em outra aba.

---

## 🧪 Verification Plan

### Automated Tests
- Rodar o conjunto `pytest tests/ -v` para garantir que o refatoramento do DB não quebre a interface do SQLite.

### Manual Verification
- Inserir **50 hosts simultâneos** no MonitorTab.
- Verificar o uso de CPU via Gerenciador de Tarefas: a meta é que a UI fique perfeitamente fluida.
- O scroll na aba Monitor deve continuar a 60 fps, sem nenhum engasgo.
