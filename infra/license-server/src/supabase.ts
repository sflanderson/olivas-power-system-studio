/**
 * Cliente mínimo do Supabase REST API.
 *
 * Sem deps externas — usa apenas `fetch` (built-in no Worker).
 * Service role key tem bypass de RLS, então este client é
 * para uso EXCLUSIVO no servidor.
 */

export interface SupabaseClient {
  url: string;
  serviceKey: string;
}

export function createClient(url: string, serviceKey: string): SupabaseClient {
  return { url: url.replace(/\/$/, ''), serviceKey };
}

interface RequestOptions {
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  path: string;
  query?: Record<string, string>;
  body?: unknown;
  prefer?: string;
}

async function request<T>(
  client: SupabaseClient,
  opts: RequestOptions,
): Promise<T> {
  const qs = opts.query
    ? '?' + new URLSearchParams(opts.query).toString()
    : '';
  const url = `${client.url}/rest/v1/${opts.path}${qs}`;
  const headers: Record<string, string> = {
    'apikey': client.serviceKey,
    'Authorization': `Bearer ${client.serviceKey}`,
    'Content-Type': 'application/json',
  };
  if (opts.prefer) headers['Prefer'] = opts.prefer;

  const resp = await fetch(url, {
    method: opts.method,
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Supabase ${opts.method} ${opts.path} ${resp.status}: ${text}`);
  }

  const text = await resp.text();
  return text ? (JSON.parse(text) as T) : (null as unknown as T);
}

// ---------------------------------------------------------------------------
// Domain helpers (typed)
// ---------------------------------------------------------------------------

export interface LicenseRow {
  id: string;
  key: string;
  key_hash: string;
  tier: string;
  customer_id: string;
  customer_email: string | null;
  customer_name: string | null;
  expiry_date: string;
  max_activations: number;
  hotmart_event_id: string | null;
  hotmart_product_id: string | null;
  hotmart_subscription_id: string | null;
  issued_at: string;
  revoked_at: string | null;
  revoked_reason: string | null;
}

export async function findLicenseByHash(
  client: SupabaseClient,
  keyHash: string,
): Promise<LicenseRow | null> {
  const rows = await request<LicenseRow[]>(client, {
    method: 'GET',
    path: 'licenses',
    query: {
      key_hash: `eq.${keyHash}`,
      revoked_at: 'is.null',
      select: '*',
      limit: '1',
    },
  });
  return rows && rows.length > 0 ? rows[0]! : null;
}

export interface ActivationRow {
  id: string;
  license_id: string;
  machine_id: string;
  activated_at: string;
  last_seen_at: string;
}

export async function findActivation(
  client: SupabaseClient,
  licenseId: string,
  machineId: string,
): Promise<ActivationRow | null> {
  const rows = await request<ActivationRow[]>(client, {
    method: 'GET',
    path: 'activations',
    query: {
      license_id: `eq.${licenseId}`,
      machine_id: `eq.${machineId}`,
      select: '*',
      limit: '1',
    },
  });
  return rows && rows.length > 0 ? rows[0]! : null;
}

export async function countActivations(
  client: SupabaseClient,
  licenseId: string,
): Promise<number> {
  const rows = await request<ActivationRow[]>(client, {
    method: 'GET',
    path: 'activations',
    query: {
      license_id: `eq.${licenseId}`,
      select: 'id',
    },
  });
  return rows ? rows.length : 0;
}

export async function insertActivation(
  client: SupabaseClient,
  licenseId: string,
  machineId: string,
  userAgent?: string,
): Promise<ActivationRow> {
  const rows = await request<ActivationRow[]>(client, {
    method: 'POST',
    path: 'activations',
    body: {
      license_id: licenseId,
      machine_id: machineId,
      user_agent: userAgent ?? null,
    },
    prefer: 'return=representation',
  });
  if (!rows || rows.length === 0) {
    throw new Error('insertActivation: no row returned');
  }
  return rows[0]!;
}

export async function touchActivation(
  client: SupabaseClient,
  activationId: string,
): Promise<void> {
  await request<unknown>(client, {
    method: 'PATCH',
    path: 'activations',
    query: { id: `eq.${activationId}` },
    body: { last_seen_at: new Date().toISOString() },
  });
}

export async function findLicenseByHotmartEvent(
  client: SupabaseClient,
  eventId: string,
): Promise<LicenseRow | null> {
  const rows = await request<LicenseRow[]>(client, {
    method: 'GET',
    path: 'licenses',
    query: {
      hotmart_event_id: `eq.${eventId}`,
      select: '*',
      limit: '1',
    },
  });
  return rows && rows.length > 0 ? rows[0]! : null;
}

export async function findLicenseBySubscriptionId(
  client: SupabaseClient,
  subscriptionId: string,
): Promise<LicenseRow | null> {
  const rows = await request<LicenseRow[]>(client, {
    method: 'GET',
    path: 'licenses',
    query: {
      hotmart_subscription_id: `eq.${subscriptionId}`,
      revoked_at: 'is.null',
      select: '*',
      limit: '1',
    },
  });
  return rows && rows.length > 0 ? rows[0]! : null;
}

export interface InsertLicenseArgs {
  key: string;
  key_hash: string;
  tier: string;
  customer_id: string;
  customer_email: string | null;
  customer_name: string | null;
  expiry_date: string;     // ISO datetime
  max_activations: number;
  hotmart_event_id?: string | null;
  hotmart_product_id?: string | null;
  hotmart_subscription_id?: string | null;
}

export async function insertLicense(
  client: SupabaseClient,
  args: InsertLicenseArgs,
): Promise<LicenseRow> {
  const rows = await request<LicenseRow[]>(client, {
    method: 'POST',
    path: 'licenses',
    body: {
      key: args.key,
      key_hash: args.key_hash,
      tier: args.tier,
      customer_id: args.customer_id,
      customer_email: args.customer_email,
      customer_name: args.customer_name,
      expiry_date: args.expiry_date,
      max_activations: args.max_activations,
      hotmart_event_id: args.hotmart_event_id ?? null,
      hotmart_product_id: args.hotmart_product_id ?? null,
      hotmart_subscription_id: args.hotmart_subscription_id ?? null,
    },
    prefer: 'return=representation',
  });
  if (!rows || rows.length === 0) {
    throw new Error('insertLicense: no row returned');
  }
  return rows[0]!;
}

export async function findLicenseById(
  client: SupabaseClient,
  licenseId: string,
): Promise<LicenseRow | null> {
  const rows = await request<LicenseRow[]>(client, {
    method: 'GET',
    path: 'licenses',
    query: {
      id: `eq.${licenseId}`,
      select: '*',
      limit: '1',
    },
  });
  return rows && rows.length > 0 ? rows[0]! : null;
}

export async function revokeLicenseByHash(
  client: SupabaseClient,
  keyHash: string,
  reason: string,
): Promise<void> {
  await request<unknown>(client, {
    method: 'PATCH',
    path: 'licenses',
    query: { key_hash: `eq.${keyHash}` },
    body: {
      revoked_at: new Date().toISOString(),
      revoked_reason: reason,
    },
  });
}

export async function logWebhook(
  client: SupabaseClient,
  args: {
    source: string;
    event_type: string;
    event_id?: string;
    payload: unknown;
    status: 'received' | 'processed' | 'failed' | 'ignored';
    error_message?: string;
  },
): Promise<void> {
  await request<unknown>(client, {
    method: 'POST',
    path: 'webhooks_log',
    body: {
      source: args.source,
      event_type: args.event_type,
      event_id: args.event_id ?? null,
      payload: args.payload,
      status: args.status,
      error_message: args.error_message ?? null,
      processed_at:
        args.status === 'processed' ? new Date().toISOString() : null,
    },
  });
}
