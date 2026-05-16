# Olivas Power System Studio — Monetization Plan

> **Status:** vigente · documento canônico · atualizar a cada sprint
> **Origem:** sessão de planejamento 2026-05-15
> **Versão alvo de lançamento comercial:** v4.1.0 (Sprint commercial 1 → 6)
> **Garantias do Master Protocol aplicáveis:** §2 (Registrar), §3 (Anti-alucinação), §8 (Context Preservation)

---

## 1. Decisões aprovadas (2026-05-15)

| # | Decisão | Justificativa |
|---|---------|---------------|
| 1 | **Dual licensing** — Apache 2.0 (Community) + EULA proprietária (Pro) | Mantém GitHub público para tração acadêmica; binário Pro fechado para venda. Possível porque o autor é único contribuidor. |
| 2 | **Hotmart Estudante R$ 29/mês** como canal prioritário no soft launch | Maior volume potencial, recorrência, ciclo curto de feedback, fiscal embutido. |
| 3 | **License server + machine fingerprint** como Sprint 1 técnico | Bloqueador real — sem isso, o stub HMAC atual é pirateável. |

## 2. Tiers e SKUs

| Tier | Distribuição | Recursos | Preço | Canal |
|------|-------------|---------|-------|-------|
| **Community** | GitHub Releases | Núcleo aberto (Apache 2.0), sem audit trail SHA256, sem AI, sem PDF profissional | R$ 0 | GitHub |
| **Estudante** | Hotmart → chave + .exe | Tudo do Pro, limitado a 5 buses, marca d'água "ACADÊMICO" | **R$ 29/mês** ou R$ 247/ano | Hotmart (recorrente) |
| **Pro Individual** | Hotmart / ML → chave + .exe | Audit trail SHA256, AI laudo (Claude via proxy), templates ABNT, suporte e-mail | R$ 89/mês ou R$ 890/ano | Hotmart + ML |
| **Pro Engenharia** | Hotmart | + biblioteca premium (relés Schneider/SEL/ABB), templates NR-10/NBR 17227 | R$ 199/mês ou R$ 1.990/ano | Hotmart |
| **Empresarial** | Venda direta + NFS-e | Multi-seat, white-label, importador ETAP/SKM, SLA | R$ 4.500–9.000/ano por seat | Site próprio |

## 3. Gate técnico (features que separam Community ↔ Pro)

| Feature | Módulo | Acesso |
|---------|--------|--------|
| Audit trail SHA256 + CREA + ART | `app/postprocessor/audit_trail.py` | Pro+ |
| Relatório HTML/PDF profissional | `app/postprocessor/report_html.py` | Pro+ |
| AI laudo (Claude via proxy backend) | `app/llm/agent.py` | Pro+ |
| Reliability Monte Carlo | `app/postprocessor/reliability_monte_carlo.py` | Pro+ |
| Arc-Flash Monte Carlo | `app/postprocessor/arc_flash_monte_carlo.py` | Pro+ |
| Power Flow Monte Carlo | `app/postprocessor/power_flow_monte_carlo.py` | Pro+ |
| Biblioteca premium relés | `app/standards/relay_models.py` + catálogos extras | Pro Engenharia+ |
| Multi-seat / multi-user | `app/integration/iec61850_client.py` (CRDT) | Empresarial |

## 4. Arquitetura técnica de licenciamento

```
[Cliente]  →  Hotmart/ML checkout
                │
                ├─ pagamento aprovado
                │
                ▼
[Webhook Receiver]  (Cloudflare Worker)
   │
   ├─ gera chave (HMAC-SHA256, formato OLV-<TIER>-<CUSTOMER>-<EXPIRY>-<HMAC>)
   ├─ grava em Supabase Postgres (tabela `licenses`)
   └─ envia e-mail (Resend) com chave + link do .exe

[Olivas Pro.exe]  (PyInstaller bundle, build separado)
   │
   ├─ primeira execução: pede chave + e-mail (LicenseDialog)
   ├─ POST /activate {key, machine_id} → JWT 30 dias
   ├─ cache local em QSettings + verificação offline até expirar
   └─ refresh automático a cada 7 dias quando online
```

### 4.1 Componentes do repo Olivas

| Arquivo | Responsabilidade |
|---------|------------------|
| `app/commercial/machine_id.py` | Hardware fingerprint (MAC + cpuid + hostname → SHA256) |
| `app/commercial/license_server_client.py` | Cliente HTTP do license server (activate/refresh/verify) |
| `app/commercial/feature_gates.py` | Decorator `@requires_tier("pro")` + helpers GUI gray-out |
| `app/commercial/license_key.py` | **Já existe** — validação HMAC (mantida como fallback offline) |
| `app/gui/license_dialog.py` | Tela de ativação (primeira execução / menu Ajuda) |
| `build/build_pro.spec` | PyInstaller config Pro (com `app/commercial/`) |
| `build/build_community.spec` | PyInstaller config Community (sem `app/commercial/` + sem MC + sem AI) |

### 4.2 Componentes da infra externa

| Pasta | Stack | Responsabilidade |
|-------|-------|------------------|
| `infra/license-server/` | Cloudflare Workers + Hono + TypeScript | Endpoints `/activate`, `/refresh`, `/revoke`, `/webhook/hotmart`, `/health` |
| `infra/license-server/db/` | Supabase Postgres | Tabela `licenses`, `activations`, `webhooks_log` |
| `infra/license-server/.env.example` | — | Vars: `HMAC_SECRET`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `HOTMART_HOTTOK`, `RESEND_API_KEY` |

## 5. Roadmap operacional (12 semanas)

| Sprint | Semana | Entrega | Critério de pronto |
|--------|--------|---------|--------------------|
| **commercial-1** | W1–W2 | `machine_id.py` + `license_server_client.py` + `feature_gates.py` + Worker skeleton + tests | Rodar `python -m app.main` em máquina limpa, ativar chave fake, destravar audit trail |
| **commercial-2** | W3 | `build/build_pro.spec` + `build/build_community.spec`. Remover `GNUATP/` e `pre-processor/` do bundle Pro | `.exe` Pro roda em Windows limpo sem Python instalado |
| **commercial-3** | W4 | EULA + ToS + Privacy LGPD (PT-BR) + abertura ME CNAE 6201-5/01 | CNPJ ativo, NFS-e emissora, conta PJ |
| **commercial-4** | W5–W6 | Webhook Hotmart `PURCHASE_APPROVED` + e-mail via Resend + tier Estudante cadastrado | Compra de teste em ambiente sandbox Hotmart libera chave automaticamente |
| **commercial-5** | W7–W8 | Landing page + vídeo demo 3 min + beta fechado com 10 engenheiros UFMG/CAUE-Br | 10 ativações reais, NPS coletado |
| **commercial-6** | W9–W12 | Soft launch público Hotmart Estudante + ML como segundo canal | Primeiras vendas externas, métricas de churn/conversão |

## 6. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Fork Apache 2.0 vendido por terceiro | Média | Alto | Marca registrada "Olivas", features Pro só no binário (sem fonte), CLA para PRs externos |
| Custo Anthropic API no tier Pro | Alta | Médio | Proxy backend com rate-limit por seat (50 msg/mês Estudante, 500 Pro, ilimitado Engenharia) |
| Hotmart Producer PJ demora 5-10 dias úteis | Alta | Médio | Iniciar abertura CNPJ em paralelo ao Sprint 1 (W1) |
| Direito de arrependimento CDC 7 dias | Certa | Baixo | Chave revogável via webhook `PURCHASE_REFUNDED` |
| Pirataria de chave (compartilhamento) | Alta | Médio | `max_activations=5` por chave + machine_id binding + revogação manual |
| `GNUATP/` e `pre-processor/` no bundle Pro | Certa se não tratar | Alto (legal) | `build_pro.spec` exclui explicitamente esses paths |

## 7. Métricas a acompanhar (pós-launch)

- **MRR Estudante:** meta W12 = R$ 580 (20 assinantes)
- **MRR Pro Individual:** meta W12 = R$ 890 (10 assinantes)
- **Churn mensal:** < 8%
- **CAC via Hotmart afiliados:** < 30% do LTV
- **Conversão landing → checkout:** > 2%
- **NPS pós-30 dias:** > 30

## 8. Documentos jurídicos a redigir (Sprint 3)

- `legal/EULA.md` — Acordo de Licença do Usuário Final (PT-BR)
- `legal/TERMS.md` — Termos de Uso (PT-BR)
- `legal/PRIVACY_LGPD.md` — Política de Privacidade conforme LGPD
- `legal/SLA.md` — Acordo de Nível de Serviço (apenas Pro Engenharia+)
- `legal/CLA.md` — Contributor License Agreement para PRs externos (preservar dual licensing)

## 9. Próxima atualização deste documento

Atualizar ao final de cada sprint commercial-X com:
- Status real vs planejado
- Mudanças de tier ou preço
- Aprendizados (especialmente do beta fechado)
- Métricas reais

---

**Fonte de verdade para roteamento de qualquer trabalho de monetização.** Antes de mudar pricing, tiers, gates ou roadmap, atualizar aqui primeiro.
