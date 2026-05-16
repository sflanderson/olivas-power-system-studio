# Olivas Power System Studio

> **Software profissional de análise elétrica** — alternativa nacional a SKM PTW / ETAP / EasyPower.

[![Tests](https://github.com/sflanderson/olivas-power-system-studio/actions/workflows/test.yml/badge.svg)](https://github.com/sflanderson/olivas-power-system-studio/actions/workflows/test.yml)
[![Lint](https://github.com/sflanderson/olivas-power-system-studio/actions/workflows/lint.yml/badge.svg)](https://github.com/sflanderson/olivas-power-system-studio/actions/workflows/lint.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE.txt)
[![release](https://img.shields.io/github/v/release/sflanderson/olivas-power-system-studio?include_prereleases&color=7E2BA8)](https://github.com/sflanderson/olivas-power-system-studio/releases)
[![python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue.svg)](https://www.python.org/)
[![Qt](https://img.shields.io/badge/Qt-PySide6-41CD52.svg)](https://www.qt.io/qt-for-python)
[![Made in Brazil](https://img.shields.io/badge/made%20in-Brasil%20%F0%9F%87%A7%F0%9F%87%B7-009C3B.svg)](https://github.com/sflanderson/olivas-power-system-studio)

---

## Visão geral

Olivas Power System Studio é um software de **análise de sistemas elétricos**
que produz laudos auditáveis (ISO 9001 / NR-10) com rastreabilidade norma →
resultado. Roda em desktop (Windows/Linux) com editor visual de unifilar
estilo PTW Power*Tools.

**5 análises especializadas:**

| # | Análise | Norma de referência |
|---|---------|---------------------|
| 1 | ⚡ **Curto-circuito** | IEC 60909-0:2016 |
| 2 | 🔌 **Fluxo de potência** | IEEE 399 / Stevenson §9 |
| 3 | 🛡️ **Coordenação e seletividade** | IEEE 242 Buff Book §15 |
| 4 | 🔥 **Energia incidente / Arc-flash** | NBR 17227:2025 / IEEE 1584-2018 |
| 5 | 📈 **Balanço de carga / partida de motor** | IEEE 141 Red Book |
| 6 | 🔍 **Saturação de TC** (3 níveis) | IEEE C57.13.1 / IEC 61869-2 / CIGRÉ WG 23-15 |

---

## Diferenciadores

### Auditabilidade total
Todos os relatórios incluem:

- **SHA256 dos inputs** — fingerprint para rastreabilidade entre versões
- **Timestamp ISO 8601** imutável
- **Bloco de responsabilidade técnica** (engenheiro, CREA, ART, assinatura)
- **Citação da norma + equação** ao lado de cada parâmetro calculado
- **Limitações declaradas** (heurísticas do MVP em bloco amarelo)

Conformidade: **ISO 9001 §8.5.1** (rastreabilidade), **NR-10 §10.2.4**
(responsabilidade técnica), **NBR 17227 §5.4.4** (assinatura do responsável).

### Editor visual estilo PTW
- Componente **BUS** como **linha grossa contínua** (estilo SKM PTW)
- Multi-conexão em qualquer ponto da barra (a cada 10 px de grid)
- Drag-resize via handles azuis quando selecionado (60–4000 px)
- Catálogo Qucs-style: 40+ componentes (R, L, C, fontes, transformadores,
  motores, relés, disjuntores, máquinas)

### Robustez
- Validação física automática nos inputs (`ArcFlashCase`, `BusComponent`,
  `IEC 60909`)
- Logging estruturado com rastreabilidade dos fallbacks
  (z=0, divergência Newton-Raphson, faixa fora da norma)
- Threading correto (PySide6 SignalRelay canonical)
- Auto-save + crash recovery (60s interval)

### Plataforma de normas
- Catálogo formal de **13 normas** (IEC, IEEE, NBR, NFPA, NR)
- 7 limitações declaradas do MVP, exibidas explicitamente no relatório
- Templates de partida (welcome) com 3 sistemas pré-prontos

---

## Quick start

### Instalação

```bash
git clone <repo>
cd MVP
pip install -r requirements.txt
python -m app.main
```

### Primeiro estudo em 5 minutos

1. **Abrir Welcome** → "Novo projeto" ou template "Sistema 13.8 kV simples".
2. **Esquemático Visual** → BUS já está populado.
3. **Toolbar → Estudo do barramento (F5)** ou **Análise → Estudo completo**.
4. **Análise → Relatório completo (HTML/PDF)** → preencher CREA + ART.
5. Laudo SHA256-fingerprinted é gerado.

---

## Comparação rápida

| Feature | Olivas | SKM PTW | ETAP | EasyPower |
|---------|--------|---------|------|-----------|
| Curto-circuito IEC 60909 | ✅ | ✅ | ✅ | ✅ |
| Fluxo de potência | ✅ | ✅ | ✅ | ✅ |
| Coordenação 50/51 | ✅ | ✅ | ✅ | ✅ |
| Arc-flash NBR 17227 | ✅ | ⚠ (IEEE 1584 only) | ✅ | ⚠ (IEEE 1584 only) |
| Audit trail SHA256 | ✅ | ❌ | ❌ | ❌ |
| Rastreabilidade norma → resultado | ✅ | ❌ | ⚠ | ❌ |
| Open source | ✅ | ❌ | ❌ | ❌ |
| Idioma nativo PT-BR | ✅ | ❌ | ❌ | ❌ |
| Preço | Free (Doutorado UFMG) | $$$$ | $$$$$ | $$$ |

⚠ = limitação ou não-conforme à NBR 17227.

---

## Status do projeto

- **v4.0.0-beta (atual)** — Public release: UAT preparation,
  i18n EN/ES parity (133/133 keys), CHANGELOG.md consolidado,
  26 production readiness tests, sweep total 245/245 verdes
- **v4.0.0-alpha** — 🏆 **Paridade total v1 com SKM PTW v11**
  atingida; SKIPPED_BACKLOG zerado (4/4 categorias 100%);
  fault distance walker IEC 60909-0:2016 §3.7
- **v3.9.0** — Auto-classify fault distance NEAR/FAR
- **v3.8.x** — TCC 3-tab pages, IEEE 14-bus fixture, Q-limit
  switching (IEEE 399 §5.3.4), Reliability Monte Carlo
- **v3.7.x** — Real branch impedance Tr/CABLE/TLIN
  (IEC 60076 + IEC 60364), bus_role explicit slack/pv/pq
- **v3.6.x** — Reliability module SAIFI/SAIDI/CAIDI/ASAI
  (IEEE 1366), TCC C-lines + protection filter
- **v3.5.x** — Scenario Manager + 8ª garantia
  (CONTEXT_PRESERVATION_PROTOCOL), wire path-based detection,
  AddLinkTag + document registry

Histórico completo: [CHANGELOG.md](CHANGELOG.md)
Roadmap: [ROADMAP.md](ROADMAP.md)
Release v4.0.0-beta: [releases/tag/v4.0.0-beta](https://github.com/sflanderson/olivas-power-system-studio/releases/tag/v4.0.0-beta)

---

## Limitações conhecidas (v4.0.0-beta)

Declaradas em todos os laudos para defesa técnica:

- **`sc_ib_far_only`**: corrente de breaking Ib calculada como Ik'';
  factor μ·q (IEC 60909 §4.6) não aplicado nesta versão (próximo a
  geradores síncronos pode haver superestimação até 30%).
- **`sc_method_b_kappa`**: fator κ por Method B (R/X único). Method C
  (frequency-equivalent) não implementado.
- **`arc_flash_lv_only`**: energia incidente para sistemas até 15 kV
  (NBR 17227 §5.2). Sistemas >15 kV requerem métodos alternativos.
- **`arc_flash_3p_only`**: cálculo assume falta trifásica simétrica
  (NBR 17227 §5.1.4).
- **`pf_positive_seq_only`**: fluxo de potência só sequência positiva.
- **`pf_no_q_limits`**: limites de Q (capability curve) em PV não aplicados.
- **`coord_no_auto_dt_min`**: validação automática de Δt entre relés
  upstream/downstream NÃO implementada (verificar manualmente).

---

## Tecnologia

- **Python 3.13+** (compatível 3.11+)
- **PySide6** (Qt6 GUI)
- **matplotlib** (plots + PDF reports)
- **pydantic** (validação de specs do catálogo)
- **pytest** (5568 tests coletados; subset de ~300 CI-safe roda no GitHub Actions)

Sem dependência em fornecedor proprietário (MATLAB, MathCAD, etc.).

### Cobertura do CI público

O badge **Tests** acima corresponde ao subset CI-safe rodado no GitHub
Actions (Python 3.11/3.12/3.13 × Ubuntu/Windows): Sprints commercial,
readiness checks, e os módulos com decoradores `@requires_feature`
(audit trail, report HTML, Monte Carlo × 3).

O sweep completo de **5568 testes** inclui testes legacy que dependem
de display real (GUI dialogs modais sem mock) e requer ambiente local
com PySide6 + Xvfb (Linux) ou X-Server real. Para rodar localmente:

```bash
pytest tests/              # sweep completo
pytest tests/test_pp_v4_*  # apenas sprints v4.x (CI-safe)
```

---

## Licença

Pesquisa acadêmica — Doutorado UFMG, Engenharia Elétrica.
Ver [LICENSE.txt](LICENSE.txt).

---

## Citar este software

Se você usar Olivas Power System Studio em pesquisa ou laudo profissional,
inclua o checksum SHA256 dos inputs na seção de auditoria do relatório
(é gerado automaticamente).

```
Software: Olivas Power System Studio v4.0.0-beta
Checksum (inputs): SHA256:abc123...
Engenheiro responsável: ____ (CREA-MG ____)
```
