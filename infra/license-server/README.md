# Olivas License Server

Cloudflare Worker que gerencia ciclo de vida de chaves de licença
do Olivas Power System Studio.

## Endpoints

| Método | Path | Função |
|--------|------|--------|
| `POST` | `/activate` | Valida chave + machine_id, retorna JWT 30 dias |
| `POST` | `/refresh` | Renova JWT antes de expirar |
| `POST` | `/revoke` | Marca chave como revogada (interno) |
| `POST` | `/webhook/hotmart` | Recebe eventos Hotmart, gera/revoga chaves |
| `GET`  | `/health` | Liveness probe |

## Stack

- **Runtime:** Cloudflare Workers (TypeScript)
- **Router:** [Hono](https://hono.dev/)
- **JWT:** [jose](https://github.com/panva/jose) (RS256, chave assimétrica)
- **DB:** Supabase Postgres (free tier)
- **Email transacional:** [Resend](https://resend.com/) (free tier 100/dia)

## Setup

```bash
cd infra/license-server
npm install
cp .env.example .dev.vars
# Editar .dev.vars com credenciais reais
npx wrangler dev
```

Para deploy:

```bash
npx wrangler secret put HMAC_SECRET
npx wrangler secret put JWT_PRIVATE_KEY
npx wrangler secret put SUPABASE_SERVICE_KEY
npx wrangler secret put HOTMART_HOTTOK
npx wrangler secret put RESEND_API_KEY
npx wrangler deploy
```

## Schema do DB

Ver `db/schema.sql`. Tabelas:

- `licenses` — uma linha por chave emitida
- `activations` — uma linha por par (key, machine_id) ativado
- `webhooks_log` — auditoria de eventos Hotmart recebidos

## Fluxo Hotmart → Chave

### Eventos cobertos (Sprint 5 — implementação real)

| Hotmart event | Ação no Worker |
|---------------|----------------|
| `PURCHASE_APPROVED` | Gera chave + INSERT `licenses` + e-mail boas-vindas (Resend) |
| `PURCHASE_REFUNDED` | Marca `revoked_at` (motivo: "estorno") + e-mail notificação |
| `PURCHASE_CHARGEBACK` | Marca `revoked_at` (motivo: "chargeback") + e-mail |
| `SUBSCRIPTION_CANCELLATION` | Marca `revoked_at` (motivo: "cancelamento") + e-mail |
| Outros | Loga em `webhooks_log` com status `ignored` |

Pipeline `PURCHASE_APPROVED`:

1. Cliente compra no Hotmart
2. Hotmart envia POST para `/webhook/hotmart` com `X-Hotmart-Hottok`
3. Worker valida hottok contra `HOTMART_HOTTOK` secret
4. Worker procura `event.id` em `licenses` (idempotência — Hotmart retenta 5x)
5. Worker mapeia `product.id` → tier via `HOTMART_PRODUCT_TIER_MAP`
6. Worker gera chave `OLV-<TIER>-<CUSTOMER>-<EXPIRY>-<HMAC>` com:
   - `customer_id` derivado de `subscription.subscriber.code` ou `purchase.transaction`
   - `expiry` = now + `TIER_VALIDITY_DAYS[tier]`
7. Worker INSERT em `licenses` com `hotmart_event_id`, `product_id`, `subscription_id`
8. Worker chama Resend para enviar e-mail com:
   - Chave
   - Link do download (`DOWNLOAD_URL_PRO`)
   - Instruções de ativação (Ctrl+L)
   - Limite de máquinas autorizadas
   - Links para EULA / Privacy / Terms

## Tier mapping (Hotmart product_id → tier)

Configurar em `src/config.ts::HOTMART_PRODUCT_TIER_MAP` após
cadastrar produtos no Hotmart Producer Console:

```ts
{
  '<id_numerico_estudante>': 'educational',     // R$ 29/mês
  '<id_numerico_pro_indiv>': 'commercial',       // R$ 89/mês
  '<id_numerico_engenharia>': 'pro_engineering', // R$ 199/mês
}
```

## Segurança

- HMAC secret nunca commitado — só via `wrangler secret`
- JWT assinado com RS256; chave pública embarcada no cliente Olivas
- Rate-limit 100 req/min por IP nos endpoints públicos
- `webhook/hotmart` valida `X-Hotmart-Hottok` antes de processar

## Status (após Sprints commercial 1–5)

| Endpoint | Status |
|----------|--------|
| `/health` | ✅ |
| `/activate` | ✅ HMAC + Supabase + JWT RS256 |
| `/refresh` | ✅ verifica JWT + re-checa Supabase + emite novo token |
| `/revoke` | ✅ admin auth via `X-Admin-Token` |
| `/webhook/hotmart` | ✅ PURCHASE_APPROVED + 3 revocation events + idempotência |

Pendente: deploy real em `wrangler deploy` após preencher
`HOTMART_PRODUCT_TIER_MAP` e configurar `RESEND_API_KEY`.
