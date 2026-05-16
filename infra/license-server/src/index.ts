/**
 * Olivas License Server — entrypoint
 *
 * Cloudflare Worker que gerencia ciclo de vida de chaves do
 * Olivas Power System Studio.
 *
 * Status v4.1.0 commercial Sprint 1:
 *   - /health                ✅
 *   - /activate              ✅ implementado (HMAC + Supabase + JWT)
 *   - /refresh               🚧 stub
 *   - /revoke                🚧 stub
 *   - /webhook/hotmart       🚧 stub (W5-6)
 */

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';

import { expiryToUnix, keyHash, validateKey } from './license';
import { signLicenseJwt, verifyLicenseJwt } from './jwt';
import {
  countActivations,
  createClient,
  findActivation,
  findLicenseById,
  findLicenseByHash,
  insertActivation,
  logWebhook,
  revokeLicenseByHash,
  touchActivation,
} from './supabase';
import { JWT_VALIDITY_SECONDS } from './config';
import { handleHotmartEvent, type HotmartEvent } from './hotmart';

type Bindings = {
  HMAC_SECRET: string;
  JWT_PRIVATE_KEY: string;
  JWT_PUBLIC_KEY: string;
  ADMIN_TOKEN: string;
  SUPABASE_URL: string;
  SUPABASE_SERVICE_KEY: string;
  HOTMART_HOTTOK: string;
  RESEND_API_KEY: string;
  ENVIRONMENT: string;
};

const app = new Hono<{ Bindings: Bindings }>();

app.use('*', logger());
app.use('*', cors({ origin: '*' }));

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

app.get('/health', (c) => {
  return c.json({
    status: 'ok',
    service: 'olivas-license-server',
    version: '0.1.0-sprint1',
    environment: c.env.ENVIRONMENT,
  });
});

// ---------------------------------------------------------------------------
// /activate
// ---------------------------------------------------------------------------

interface ActivateRequest {
  key: string;
  machine_id: string;
}

app.post('/activate', async (c) => {
  let body: ActivateRequest;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: 'invalid_json' }, 400);
  }

  if (!body.key || !body.machine_id) {
    return c.json({ error: 'missing_fields' }, 400);
  }

  // 1) Validar formato + HMAC da chave
  const parsed = await validateKey(body.key, c.env.HMAC_SECRET);
  if (!parsed) {
    return c.json({ error: 'invalid_key' }, 401);
  }

  // 2) Buscar no Supabase
  const supabase = createClient(c.env.SUPABASE_URL, c.env.SUPABASE_SERVICE_KEY);
  const hash = await keyHash(body.key);
  const license = await findLicenseByHash(supabase, hash);
  if (!license) {
    return c.json({ error: 'key_not_found_or_revoked' }, 404);
  }

  // 3) Verificar expiração da chave
  const expiryUnix = expiryToUnix(parsed.expiry_yyyymmdd);
  const now = Math.floor(Date.now() / 1000);
  if (expiryUnix < now) {
    return c.json({ error: 'key_expired' }, 410);
  }

  // 4) Verificar quota de ativações
  const existing = await findActivation(
    supabase,
    license.id,
    body.machine_id,
  );

  if (!existing) {
    const used = await countActivations(supabase, license.id);
    if (used >= license.max_activations) {
      return c.json(
        {
          error: 'max_activations_exceeded',
          max_activations: license.max_activations,
        },
        403,
      );
    }
    await insertActivation(
      supabase,
      license.id,
      body.machine_id,
      c.req.header('User-Agent') ?? undefined,
    );
  } else {
    await touchActivation(supabase, existing.id);
  }

  // 5) Assinar JWT (validade = MIN(expiry da chave, JWT_VALIDITY_SECONDS))
  const jwtExp = Math.min(expiryUnix, now + JWT_VALIDITY_SECONDS);
  const token = await signLicenseJwt(c.env.JWT_PRIVATE_KEY, {
    tier: license.tier,
    sub: license.customer_id,
    exp: jwtExp,
    machine_id: body.machine_id,
    license_id: license.id,
  });

  return c.json({
    token,
    tier: license.tier,
    customer_id: license.customer_id,
    expiry_unix: jwtExp,
    license_expiry_unix: expiryUnix,
  });
});

// ---------------------------------------------------------------------------
// /refresh
// ---------------------------------------------------------------------------

interface RefreshRequest {
  token: string;
}

app.post('/refresh', async (c) => {
  let body: RefreshRequest;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: 'invalid_json' }, 400);
  }

  if (!body.token) {
    return c.json({ error: 'missing_token' }, 400);
  }

  // 1) Verificar JWT atual
  const payload = await verifyLicenseJwt(c.env.JWT_PUBLIC_KEY, body.token);
  if (!payload) {
    return c.json({ error: 'invalid_token' }, 401);
  }

  // 2) Re-checar revogação no Supabase
  const supabase = createClient(c.env.SUPABASE_URL, c.env.SUPABASE_SERVICE_KEY);
  const license = await findLicenseById(supabase, payload.license_id);
  if (!license || license.revoked_at) {
    return c.json({ error: 'license_revoked' }, 410);
  }

  // 3) Touch activation (last_seen_at)
  const activation = await findActivation(
    supabase,
    license.id,
    payload.machine_id,
  );
  if (!activation) {
    return c.json({ error: 'activation_missing' }, 410);
  }
  await touchActivation(supabase, activation.id);

  // 4) Re-checar expiração absoluta da chave
  const expiryUnix = Math.floor(new Date(license.expiry_date).getTime() / 1000);
  const now = Math.floor(Date.now() / 1000);
  if (expiryUnix < now) {
    return c.json({ error: 'key_expired' }, 410);
  }

  // 5) Emitir novo JWT
  const jwtExp = Math.min(expiryUnix, now + JWT_VALIDITY_SECONDS);
  const newToken = await signLicenseJwt(c.env.JWT_PRIVATE_KEY, {
    tier: license.tier,
    sub: license.customer_id,
    exp: jwtExp,
    machine_id: payload.machine_id,
    license_id: license.id,
  });

  return c.json({
    token: newToken,
    tier: license.tier,
    customer_id: license.customer_id,
    expiry_unix: jwtExp,
    license_expiry_unix: expiryUnix,
  });
});

// ---------------------------------------------------------------------------
// /revoke (interno — autenticado via X-Admin-Token)
// ---------------------------------------------------------------------------

interface RevokeRequest {
  key: string;
  reason?: string;
}

app.post('/revoke', async (c) => {
  const adminToken = c.req.header('X-Admin-Token');
  if (!adminToken || adminToken !== c.env.ADMIN_TOKEN) {
    return c.json({ error: 'unauthorized' }, 401);
  }

  let body: RevokeRequest;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: 'invalid_json' }, 400);
  }

  if (!body.key) {
    return c.json({ error: 'missing_key' }, 400);
  }

  const supabase = createClient(c.env.SUPABASE_URL, c.env.SUPABASE_SERVICE_KEY);
  const hash = await keyHash(body.key);

  const license = await findLicenseByHash(supabase, hash);
  if (!license) {
    return c.json({ error: 'key_not_found' }, 404);
  }

  await revokeLicenseByHash(supabase, hash, body.reason ?? 'manual_revoke');

  return c.json({
    status: 'revoked',
    license_id: license.id,
    customer_id: license.customer_id,
  });
});

// ---------------------------------------------------------------------------
// /webhook/hotmart
// ---------------------------------------------------------------------------

app.post('/webhook/hotmart', async (c) => {
  const hottok = c.req.header('X-Hotmart-Hottok');
  if (!hottok || hottok !== c.env.HOTMART_HOTTOK) {
    return c.json({ error: 'unauthorized' }, 401);
  }

  let event: HotmartEvent;
  try {
    event = (await c.req.json()) as HotmartEvent;
  } catch {
    return c.json({ error: 'invalid_json' }, 400);
  }

  if (!event?.event || !event?.id) {
    return c.json({ error: 'missing_event_fields' }, 400);
  }

  const supabase = createClient(c.env.SUPABASE_URL, c.env.SUPABASE_SERVICE_KEY);

  try {
    const result = await handleHotmartEvent(
      { HMAC_SECRET: c.env.HMAC_SECRET, RESEND_API_KEY: c.env.RESEND_API_KEY },
      supabase,
      event,
    );
    return c.json({ ...result, event_type: event.event }, 200);
  } catch (e) {
    // Log e devolve 500 — Hotmart retentará até 5 vezes
    await logWebhook(supabase, {
      source: 'hotmart',
      event_type: event.event,
      event_id: event.id,
      payload: event,
      status: 'failed',
      error_message: String(e),
    });
    return c.json({ error: 'internal_error' }, 500);
  }
});

// ---------------------------------------------------------------------------
// 404
// ---------------------------------------------------------------------------

app.notFound((c) => c.json({ error: 'not_found' }, 404));

export default app;
