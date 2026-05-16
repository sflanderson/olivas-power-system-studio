# Olivas Power System Studio — Roadmap v0.94 → v1.0

> **Documento de navegação estratégica** — atualize este arquivo ao concluir cada sprint.

## Visão geral

Elevar o score de **72/100 → 95/100** em ~6 meses (12 sprints).

| Fase | Versões | Foco | Score | Status |
|---|---|---|---|---|
| **1. Bloqueadores** | v0.95–v0.98 | Cable, V-drop, Harmonics, Library | 72→85 | 🔄 Em andamento |
| **2. Match comercial** | v0.99–v0.103 | TCC, PF unbalanced, HV AF, Reaccel, Grid | 85→92 | ⏳ Pendente |
| **3. Diferenciação** | v0.104–v1.0 | AI laudos, Plugin, Cloud, ABNT | 92→95+ | ⏳ Pendente |

## Sprint Status

| Sprint | Versão | Conteúdo | Tests | Status |
|---|---|---|---|---|
| 1 | v0.95.0 | Cable Sizing (NBR 5410) | 26/26 | ✅ Concluído |
| 2 | v0.96.0 | Voltage Drop Profile | 15/15 | ✅ Concluído |
| 3 | v0.97.0 | Harmonics (IEEE 519) | 17/17 | ✅ Concluído |
| 4 | v0.98.0 | Equipment Library (33 entries, 5 vendors) | 28/28 | ✅ Concluído — **FASE 1 COMPLETA** |
| 5 | v0.99.0 | TCC Curves + Coordination Check | 15/15 | ✅ Concluído |
| 6 | v0.100.0 | PF Unbalanced (seq 0/1/2 + IEEE 1159) | 12/12 | ✅ Concluído |
| 7 | v0.101.0 | Arc-flash HV (EPRI 2011 + Terzija-Konglin) | 19/19 | ✅ Concluído |
| 8 | v0.102.0 | Motor Reaccel + Black Start | 12/12 | ✅ Concluído |
| 9 | v0.103.0 | Ground Grid (IEEE 80) | 15/15 | ✅ Concluído — **FASE 2 COMPLETA** |
| 10 | v0.104.0 | AI-Driven Laudos (Claude offline+online) | 12/12 | ✅ Concluído |
| 11 | v0.105.0 | Plugin Ecosystem | 7/7 | ✅ Concluído |
| 12 | v1.0.0 | RELEASE PÚBLICA (Score 95/100) | — | ✅ Entregue |

## Quality Gates (cada sprint)

- [ ] Tests passing: 100% novos + sweep regression
- [ ] Coverage: módulo novo ≥ 85%
- [ ] CHANGELOG entry detalhada
- [ ] Audit trail integrado (se análise)
- [ ] Smoke test em projeto real

Ver detalhes em: ver mensagem de chat anterior — "Plano para subir o nível".
