/**
 * License key generation and validation.
 *
 * Formato: OLV-<TIER_CODE>-<CUSTOMER_ID>-<EXPIRY>-<HMAC8>
 *
 * Compatível com app/commercial/license_key.py — o HMAC é truncado
 * em 8 hex chars para caber em chave humana-legível.
 */

const TIER_CODE_MAP: Record<string, string> = {
  educational: 'EDU',
  demo: 'DEMO',
  commercial: 'COMM',
  pro_engineering: 'PROE',
  enterprise: 'ENT',
};

const CODE_TIER_MAP: Record<string, string> = Object.fromEntries(
  Object.entries(TIER_CODE_MAP).map(([k, v]) => [v, k]),
);

const enc = new TextEncoder();

async function hmacSha256Hex(secret: string, msg: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    enc.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(msg));
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export interface ParsedKey {
  tier: string;        // canonical (e.g., "commercial")
  tier_code: string;   // 3-4 chars in key
  customer_id: string; // alphanumeric
  expiry_yyyymmdd: string;
  hmac_truncated: string;
}

export function parseKeyFormat(key: string): ParsedKey | null {
  const parts = key.split('-');
  if (parts.length !== 5 || parts[0] !== 'OLV') return null;

  const [, tier_code, customer_id, expiry_yyyymmdd, hmac_truncated] = parts;
  if (!tier_code || !customer_id || !expiry_yyyymmdd || !hmac_truncated) {
    return null;
  }
  const tier = CODE_TIER_MAP[tier_code.toUpperCase()];
  if (!tier) return null;

  return {
    tier,
    tier_code: tier_code.toUpperCase(),
    customer_id,
    expiry_yyyymmdd,
    hmac_truncated: hmac_truncated.toUpperCase(),
  };
}

export async function validateKey(
  key: string,
  hmacSecret: string,
): Promise<ParsedKey | null> {
  const parsed = parseKeyFormat(key);
  if (!parsed) return null;

  const msg = `OLV-${parsed.tier_code}-${parsed.customer_id}-${parsed.expiry_yyyymmdd}`;
  const expectedFull = await hmacSha256Hex(hmacSecret, msg);
  const expected = expectedFull.slice(0, 8).toUpperCase();

  if (expected !== parsed.hmac_truncated) return null;
  return parsed;
}

export async function generateKey(
  hmacSecret: string,
  args: {
    tier: string;
    customer_id: string;
    expiry_yyyymmdd: string;
  },
): Promise<string> {
  const tier_code = TIER_CODE_MAP[args.tier];
  if (!tier_code) throw new Error(`unknown tier: ${args.tier}`);

  const msg = `OLV-${tier_code}-${args.customer_id}-${args.expiry_yyyymmdd}`;
  const full = await hmacSha256Hex(hmacSecret, msg);
  const truncated = full.slice(0, 8).toUpperCase();
  return `${msg}-${truncated}`;
}

export function expiryToUnix(yyyymmdd: string): number {
  const y = parseInt(yyyymmdd.slice(0, 4), 10);
  const m = parseInt(yyyymmdd.slice(4, 6), 10) - 1;
  const d = parseInt(yyyymmdd.slice(6, 8), 10);
  return Math.floor(Date.UTC(y, m, d, 23, 59, 59) / 1000);
}

export async function keyHash(key: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', enc.encode(key));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}
