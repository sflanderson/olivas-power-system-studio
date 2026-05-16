/**
 * Hotmart webhook event handlers.
 *
 * Documentação de eventos:
 * https://developers.hotmart.com/docs/pt-BR/webhook/about-webhook/
 *
 * Eventos cobertos:
 * - PURCHASE_APPROVED         → gera chave + e-mail boas-vindas
 * - PURCHASE_REFUNDED         → revoga (motivo: estorno)
 * - PURCHASE_CHARGEBACK       → revoga (motivo: chargeback)
 * - SUBSCRIPTION_CANCELLATION → revoga ao fim do período pago
 *
 * Idempotência: cada PURCHASE_APPROVED tem `id` único. Antes
 * de gerar chave, verifica `findLicenseByHotmartEvent(event_id)`
 * — se já existe, apenas retorna OK (Hotmart pode tentar
 * reenviar até 5 vezes em caso de timeout).
 */

import { generateKey, keyHash } from './license';
import {
  HOTMART_PRODUCT_TIER_MAP,
  TIER_VALIDITY_DAYS,
  MAX_ACTIVATIONS_PER_KEY,
  TIER_LABEL_PT,
  DOWNLOAD_URL_PRO,
  EMAIL_FROM,
} from './config';
import { createResendClient, sendEmail } from './resend';
import { welcomeKeyEmail, revocationEmail } from './email_templates';
import {
  type SupabaseClient,
  findLicenseByHotmartEvent,
  findLicenseBySubscriptionId,
  insertLicense,
  logWebhook,
  revokeLicenseByHash,
} from './supabase';


export interface HotmartEnv {
  HMAC_SECRET: string;
  RESEND_API_KEY: string;
}


interface HotmartBuyer {
  email: string;
  name?: string;
}

interface HotmartProduct {
  id: number | string;
  name?: string;
}

interface HotmartPurchase {
  transaction: string;
  approved_date?: number;
  status?: string;
}

interface HotmartSubscription {
  subscriber?: { code?: string };
  code?: string;
  plan?: { id?: number; name?: string };
}

export interface HotmartEvent {
  id: string;
  event: string;          // "PURCHASE_APPROVED", "PURCHASE_REFUNDED", etc
  version?: string;
  data: {
    buyer?: HotmartBuyer;
    product?: HotmartProduct;
    purchase?: HotmartPurchase;
    subscription?: HotmartSubscription;
  };
}


// ---------------------------------------------------------------------------
// PURCHASE_APPROVED
// ---------------------------------------------------------------------------


function _yyyymmdd(daysFromNow: number): string {
  const d = new Date(Date.now() + daysFromNow * 86400 * 1000);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  return `${y}${m}${day}`;
}


function _customerIdFromEvent(ev: HotmartEvent): string {
  // Preferência: subscription.subscriber.code → transaction → email hash
  const sub = ev.data.subscription;
  if (sub?.subscriber?.code) {
    return sub.subscriber.code.replace(/[^A-Za-z0-9]/g, '').slice(0, 10).toUpperCase();
  }
  if (sub?.code) {
    return sub.code.replace(/[^A-Za-z0-9]/g, '').slice(0, 10).toUpperCase();
  }
  if (ev.data.purchase?.transaction) {
    return ev.data.purchase.transaction
      .replace(/[^A-Za-z0-9]/g, '')
      .slice(0, 10)
      .toUpperCase();
  }
  // Fallback: hash do e-mail (não-PII no formato chave — só prefixo)
  const email = ev.data.buyer?.email ?? 'unknown';
  let h = 0;
  for (const c of email) h = (h * 31 + c.charCodeAt(0)) % 1_000_000_000;
  return `E${String(h).padStart(9, '0')}`;
}


export async function handlePurchaseApproved(
  env: HotmartEnv,
  supabase: SupabaseClient,
  ev: HotmartEvent,
): Promise<{ status: 'created' | 'duplicate' | 'unknown_product'; licenseKey?: string }> {
  // Idempotência
  const existing = await findLicenseByHotmartEvent(supabase, ev.id);
  if (existing) {
    return { status: 'duplicate', licenseKey: existing.key };
  }

  const productId = String(ev.data.product?.id ?? '');
  const tier = HOTMART_PRODUCT_TIER_MAP[productId];
  if (!tier) {
    await logWebhook(supabase, {
      source: 'hotmart',
      event_type: ev.event,
      event_id: ev.id,
      payload: ev,
      status: 'ignored',
      error_message: `product_id ${productId} não mapeado em HOTMART_PRODUCT_TIER_MAP`,
    });
    return { status: 'unknown_product' };
  }

  const validityDays = TIER_VALIDITY_DAYS[tier] ?? 30;
  const maxActivations = MAX_ACTIVATIONS_PER_KEY[tier] ?? 1;
  const tierLabel = TIER_LABEL_PT[tier] ?? tier;

  const customerId = _customerIdFromEvent(ev);
  const expiryYYYYMMDD = _yyyymmdd(validityDays);

  const key = await generateKey(env.HMAC_SECRET, {
    tier,
    customer_id: customerId,
    expiry_yyyymmdd: expiryYYYYMMDD,
  });
  const hash = await keyHash(key);

  const expiryDate = new Date(
    Date.now() + validityDays * 86400 * 1000,
  ).toISOString();

  const license = await insertLicense(supabase, {
    key,
    key_hash: hash,
    tier,
    customer_id: customerId,
    customer_email: ev.data.buyer?.email ?? null,
    customer_name: ev.data.buyer?.name ?? null,
    expiry_date: expiryDate,
    max_activations: maxActivations,
    hotmart_event_id: ev.id,
    hotmart_product_id: productId,
    hotmart_subscription_id:
      ev.data.subscription?.code ?? ev.data.purchase?.transaction ?? null,
  });

  // E-mail boas-vindas
  if (ev.data.buyer?.email) {
    const resend = createResendClient(env.RESEND_API_KEY, EMAIL_FROM);
    const tmpl = welcomeKeyEmail({
      customerName: ev.data.buyer.name ?? '',
      customerEmail: ev.data.buyer.email,
      licenseKey: key,
      tier,
      tierLabel,
      expiryDate: expiryDate.slice(0, 10),
      downloadUrl: DOWNLOAD_URL_PRO,
      maxActivations,
    });
    try {
      await sendEmail(resend, {
        to: ev.data.buyer.email,
        subject: tmpl.subject,
        html: tmpl.html,
        text: tmpl.text,
        tags: [
          { name: 'kind', value: 'welcome_key' },
          { name: 'tier', value: tier },
        ],
      });
    } catch (e) {
      // Não falha o webhook — chave já foi gerada e gravada
      await logWebhook(supabase, {
        source: 'hotmart',
        event_type: ev.event,
        event_id: ev.id,
        payload: { error: String(e) },
        status: 'failed',
        error_message: `resend failed: ${String(e)}`,
      });
    }
  }

  await logWebhook(supabase, {
    source: 'hotmart',
    event_type: ev.event,
    event_id: ev.id,
    payload: ev,
    status: 'processed',
  });

  return { status: 'created', licenseKey: license.key };
}


// ---------------------------------------------------------------------------
// Eventos de revogação
// ---------------------------------------------------------------------------


export async function handleRevocationEvent(
  env: HotmartEnv,
  supabase: SupabaseClient,
  ev: HotmartEvent,
  reasonLabel: string,
): Promise<{ status: 'revoked' | 'not_found' }> {
  const subscriptionId =
    ev.data.subscription?.code ?? ev.data.purchase?.transaction ?? null;

  if (!subscriptionId) {
    await logWebhook(supabase, {
      source: 'hotmart',
      event_type: ev.event,
      event_id: ev.id,
      payload: ev,
      status: 'failed',
      error_message: 'missing subscription/transaction id',
    });
    return { status: 'not_found' };
  }

  const license = await findLicenseBySubscriptionId(supabase, subscriptionId);
  if (!license) {
    await logWebhook(supabase, {
      source: 'hotmart',
      event_type: ev.event,
      event_id: ev.id,
      payload: ev,
      status: 'ignored',
      error_message: 'license not found for subscription',
    });
    return { status: 'not_found' };
  }

  await revokeLicenseByHash(supabase, license.key_hash, reasonLabel);

  // E-mail de notificação (best-effort)
  if (license.customer_email) {
    const tierLabel = TIER_LABEL_PT[license.tier] ?? license.tier;
    try {
      const resend = createResendClient(env.RESEND_API_KEY, EMAIL_FROM);
      const tmpl = revocationEmail({
        customerName: license.customer_name ?? '',
        customerEmail: license.customer_email,
        tierLabel,
        reason: reasonLabel,
      });
      await sendEmail(resend, {
        to: license.customer_email,
        subject: tmpl.subject,
        html: tmpl.html,
        text: tmpl.text,
        tags: [
          { name: 'kind', value: 'revocation' },
          { name: 'reason', value: reasonLabel },
        ],
      });
    } catch {
      // Não falha o webhook — revogação já está gravada
    }
  }

  await logWebhook(supabase, {
    source: 'hotmart',
    event_type: ev.event,
    event_id: ev.id,
    payload: ev,
    status: 'processed',
  });
  return { status: 'revoked' };
}


// ---------------------------------------------------------------------------
// Router central
// ---------------------------------------------------------------------------


export async function handleHotmartEvent(
  env: HotmartEnv,
  supabase: SupabaseClient,
  ev: HotmartEvent,
): Promise<{ status: string; details?: unknown }> {
  switch (ev.event) {
    case 'PURCHASE_APPROVED':
      return {
        status: 'purchase_approved',
        details: await handlePurchaseApproved(env, supabase, ev),
      };
    case 'PURCHASE_REFUNDED':
      return {
        status: 'purchase_refunded',
        details: await handleRevocationEvent(env, supabase, ev, 'estorno'),
      };
    case 'PURCHASE_CHARGEBACK':
      return {
        status: 'purchase_chargeback',
        details: await handleRevocationEvent(env, supabase, ev, 'chargeback'),
      };
    case 'SUBSCRIPTION_CANCELLATION':
      return {
        status: 'subscription_cancellation',
        details: await handleRevocationEvent(env, supabase, ev, 'cancelamento'),
      };
    default:
      // Eventos não interessantes: PURCHASE_DELAYED, PURCHASE_EXPIRED,
      // PURCHASE_OUT_OF_SHOPPING_CART, SWITCH_PLAN, etc.
      await logWebhook(supabase, {
        source: 'hotmart',
        event_type: ev.event,
        event_id: ev.id,
        payload: ev,
        status: 'ignored',
        error_message: 'event type not handled',
      });
      return { status: 'ignored', details: { event: ev.event } };
  }
}
