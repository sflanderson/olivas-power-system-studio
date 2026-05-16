# v4.0.0-beta — UAT Preparation + Public Release

Primeiro release público do Olivas Power System Studio.
Software desktop em Python/PySide6 para análise de sistemas elétricos
auditáveis (alternativa nacional brasileira a SKM PTW / ETAP / EasyPower).

## ✨ Destaques

- 🏆 **Paridade total SKM PTW v11** atingida em v4.0.0-alpha
  (SKIPPED_BACKLOG zerado, 4/4 categorias 100%)
- 🔬 **5 análises auditáveis**:
  - Curto-circuito (IEC 60909-0:2016)
  - Fluxo de potência (IEEE 399 Brown Book + Stevenson §9)
  - Coordenação e seletividade (IEEE 242 Buff Book §15)
  - Energia incidente / arc-flash (NBR 17227:2025 + IEEE 1584-2018)
  - Balanço de carga / partida de motor (IEEE 141 Red Book)
- 🛡️ **Audit trail**: SHA256 dos inputs + CREA + ART + citação norma →
  resultado em todos os relatórios (ISO 9001 §8.5.1 + NR-10 §10.2.4
  + NBR 17227 §5.4.4)
- 🌐 **i18n PT/EN/ES**: 133/133 keys parity em todos os idiomas
- 🔌 **Plugin marketplace** + Scenario Manager + Reliability MC +
  Arc-Flash MC + Power Flow MC
- 📊 245 tests verdes (sweep) + 26 readiness tests específicos

## 🧪 Standards cobertos

| Tipo | Standards |
|------|-----------|
| Curto-circuito | IEC 60909-0:2016 |
| Transformadores | IEC 60076-1:2011 |
| Cabos | IEC 60364-5-52:2009 |
| Confiabilidade | IEEE 1366-2012, IEEE 493-2007 |
| Power flow | IEEE 399-1997 |
| Arc flash | IEEE 1584-2018, NBR 17227:2025 |
| Coordenação | IEEE 242-2001 |
| Segurança elétrica | NFPA 70E:2024, NR-10 |
| Instalações BT | NBR 5410 |
| Saturação de TC | IEEE C57.13.1-2017, IEC 61869-2:2012, CIGRÉ WG 23-15 |

## 🚀 Como começar

```bash
git clone https://github.com/sflanderson/olivas-power-system-studio.git
cd olivas-power-system-studio
pip install -r requirements.txt
python -m app.main
```

## ⚠ Status: BETA

- ✅ UAT prep concluído, 245/245 testes verdes
- ⚠ Não-production ainda — requer:
  - Performance profiling em projetos grandes (100+ buses)
  - PyInstaller distribution test em ambientes limpos
  - User feedback loop de beta testers
  - Documentação localizada (manual EN/ES)

## 📋 Limitações declaradas (em todos os laudos)

Conforme `README.md`, esta versão declara explicitamente em cada
relatório:

- `sc_ib_far_only`, `sc_method_b_kappa` (curto-circuito)
- `arc_flash_lv_only`, `arc_flash_3p_only` (arc-flash)
- `pf_positive_seq_only`, `pf_no_q_limits` (power flow)
- `coord_no_auto_dt_min` (coordenação)

Detalhes em `docs/SKIPPED_BACKLOG.md` (atualmente zerado) e nos
`docs/v*_HANDOFF.md`.

## 📜 Licença

**Apache 2.0** — ver [LICENSE.txt](../LICENSE.txt).

Notice de terceiros em [docs/THIRD_PARTY_NOTICES.md](../docs/THIRD_PARTY_NOTICES.md).
Política clean-room em [docs/LICENSING.md](../docs/LICENSING.md).

## 🔗 Citação acadêmica

Doutorado UFMG — Engenharia Elétrica — Landerson Ferreira Silva.

```bibtex
@software{olivas_power_system_studio_2026,
  author  = {Silva, Landerson Ferreira},
  title   = {Olivas Power System Studio v4.0.0-beta},
  year    = {2026},
  url     = {https://github.com/sflanderson/olivas-power-system-studio},
  institution = {Universidade Federal de Minas Gerais}
}
```

## 🛤 Próximas etapas (v4.1+)

Roadmap completo em [ROADMAP.md](../ROADMAP.md):

- v4.1: Real wire-graph BFS, Multi-source IEC 60909 aggregation
- v4.2: Multi-state Markov reliability
- v4.3: IEEE 519 deep harmonics
- Comercial: monetização via assinaturas Hotmart + Mercado Livre
  (workflow técnico fechado, aguardando frente jurídica/fiscal)
