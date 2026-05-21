# NOCPing

Ferramenta de diagnóstico de rede para analistas NOC, desenvolvida em Python + PyQt6.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green?logo=qt)
![Platform](https://img.shields.io/badge/Windows-10%2F11-0078D4?logo=windows)
![Platform](https://img.shields.io/badge/Linux-Ubuntu%2FDebian-E95420?logo=ubuntu)
![Platform](https://img.shields.io/badge/macOS-12+-000000?logo=apple)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## Screenshots

### Monitor de Hosts
![Monitor](screenshots/monitor.png)
> Monitoramento em tempo real com gráfico de RTT, estatísticas e exportação CSV/JSON.

### Port Scan
![Port Scan](screenshots/portscan.png)
> Varredura TCP/UDP com progresso em tempo real, presets e suporte a UDP open|filtered.

### Banner Grab / TLS
![Banner TLS](screenshots/banner.png)
> Inspeção de banner HTTP e detalhes do certificado TLS/SSL.

### Traceroute
![Traceroute](screenshots/traceroute.png)
> Traceroute ICMP com resolução DNS reversa por hop.

---

## Funcionalidades

| Aba | Recursos |
|-----|----------|
| **Monitor** | Multi-host TCP/ICMP/UDP, gráfico RTT, stats, exportar CSV/JSON, salva sessão |
| **Port Scan** | TCP+UDP, Top 20/100/All, progress bar, UDP open\|filtered, exportar CSV |
| **Banner/TLS** | Banner HTTP, versão TLS, cipher suite, CN e validade do certificado |
| **Traceroute** | ICMP TTL, DNS reverso com timeout 2s por hop, tabela Hop/IP/RTT |

---

## Download

Baixe o executável na página de [**Releases**](https://github.com/heitortpf/nocping/releases) — sem instalar Python ou dependências.

| Sistema | Arquivo |
|---------|---------|
| Windows 10/11 (64-bit) | `NOCPing-Windows.exe` |
| Linux (Ubuntu/Debian x64) | `NOCPing-Linux` |
| macOS 12+ (ARM/Intel) | `NOCPing-macOS` |

---

## Como usar

### Windows
1. Baixe `NOCPing-Windows.exe`
2. Clique duas vezes para abrir
3. Para ICMP e UDP: clique com botão direito → **Executar como administrador**

### Linux
```bash
chmod +x NOCPing-Linux
./NOCPing-Linux

# Para ICMP e UDP (requer root):
sudo ./NOCPing-Linux
```

### macOS
```bash
chmod +x NOCPing-macOS
# Primeira execução — liberar Gatekeeper:
xattr -cr NOCPing-macOS
./NOCPing-macOS

# Para ICMP e UDP (requer root):
sudo ./NOCPing-macOS
```

> **Nota:** TCP Port Scan funciona sem privilégios em todos os sistemas.

---

## Instalar via código-fonte

```bash
git clone https://github.com/heitortpf/nocping.git
cd nocping
pip install -r requirements.txt
python main.py
```

**Requisitos:**

| Dependência | Versão mínima |
|-------------|---------------|
| Python      | 3.11+         |
| PyQt6       | 6.6+          |
| pyqtgraph   | 0.13+         |
| darkdetect  | 0.8+          |

---

## Gerar o executável localmente

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name NOCPing --icon NOCPing.ico main.py
# Saída: dist/NOCPing.exe  (ou NOCPing no Linux/macOS)
```

---

## Testes

```bash
# CI-safe (sem rede ou admin):
pytest tests/ -v -m "not live"

# Completo (requer rede):
pytest tests/ -v
```

65 testes automatizados cobrindo `core/network`, `core/config_store`, `ui/widgets/_utils` e QThread workers.

---

## Tema claro / escuro

Detectado automaticamente pelo SO via `darkdetect`. Alternar manualmente: `Ctrl+T`.  
Múltiplas janelas com `Ctrl+N` sincronizam o tema entre si.

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

## Licença

MIT
