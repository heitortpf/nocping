# NOCPing

Ferramenta de diagnóstico de rede para analistas NOC, desenvolvida em Python + PyQt6.

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green?logo=qt)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey?logo=windows)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## Funcionalidades

### Monitor de Hosts
- Monitoramento simultâneo de múltiplos hosts via TCP, ICMP ou UDP
- Gráfico de RTT em tempo real por host
- Estatísticas: RTT atual, média, mínimo, máximo e perda de pacotes
- Salva e restaura automaticamente a lista de hosts entre sessões
- Exportar histórico de RTT de cada host para CSV
- Exportar resumo de todos os hosts para CSV ou JSON

### Port Scan
- Varredura TCP e UDP com controle de concorrência
- Presets: Top 20, Top 100, Todas as portas (1–65535) ou intervalo personalizado
- Barra de progresso em tempo real
- Suporte a TCP+UDP simultâneo
- Opção de exibir portas UDP `open|filtered` (sem resposta ICMP unreachable)

### Banner Grab / TLS
- Conexão TCP com envio de requisição HTTP HEAD
- Inspeção TLS/SSL: versão do protocolo, cipher suite, CN do certificado e validade

### Traceroute
- Traceroute ICMP com TTL crescente
- Resolução DNS reversa por hop (com timeout de 2s para não travar)
- Tabela com hop, IP, hostname, RTT e notas

---

## Requisitos

| Componente | Versão mínima |
|------------|---------------|
| Python     | 3.11+         |
| PyQt6      | 6.6+          |
| pyqtgraph  | 0.13+         |
| darkdetect | 0.8+          |
| Windows    | 10 / 11 (64-bit) |

> **ICMP e UDP** requerem execução como **Administrador**.  
> **TCP Port Scan** funciona sem privilégios elevados.

---

## Instalação

```bash
git clone https://github.com/heitortpf/nocping.git
cd nocping
pip install -r requirements.txt
python main.py
```

---

## Executável standalone

Baixe o `NOCPing.exe` na página de [Releases](https://github.com/heitortpf/nocping/releases) e execute diretamente — sem instalar Python ou qualquer dependência.

Para gerar o `.exe` localmente:

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "NOCPing" main.py
# Saída: dist/NOCPing.exe
```

---

## Testes

```bash
# Todos os testes (CI-safe, sem rede ou admin):
pytest tests/ -v -m "not live"

# Incluindo testes que requerem rede:
pytest tests/ -v
```

65 testes automatizados cobrindo: `core/network`, `core/config_store`, `ui/widgets/_utils` e workers Qt.

---

## Estrutura do projeto

```
main.py                  — entry point
core/
  models.py              — dataclasses e enums
  network.py             — funções de rede puras
  workers.py             — QThread workers com sinais PyQt6
  config_store.py        — persistência da lista de hosts
ui/
  main_window.py         — janela principal, temas, multi-janela
  monitor_tab.py         — aba de monitoramento
  scan_tab.py            — aba de port scan
  banner_tab.py          — aba de banner grab / TLS
  traceroute_tab.py      — aba de traceroute
  widgets/
    host_card.py         — card individual de host
    rtt_graph.py         — gráfico RTT em tempo real
    _utils.py            — helpers e estilos compartilhados
tests/
  test_network.py
  test_config_store.py
  test_rtt_utils.py
  test_workers.py
```

---

## Tema claro / escuro

O tema é detectado automaticamente pelo sistema operacional via `darkdetect`. Para alternar manualmente: `Ctrl+T`. Múltiplas janelas (`Ctrl+N`) sincronizam o tema entre si.

---

## Licença

MIT
