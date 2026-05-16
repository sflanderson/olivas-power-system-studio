/**
 * Olivas License Server — configuração estática.
 *
 * Mapeia product_id Hotmart para tier interno do Olivas.
 * Preencher product_id reais após cadastrar produtos no
 * Hotmart Producer Console.
 */

export const HOTMART_PRODUCT_TIER_MAP: Record<string, string> = {
  // Preencher após cadastro em hotmart.com/producer
  // 'NUMERIC_PRODUCT_ID': 'tier_interno',
  // Exemplo:
  //   '1234567': 'educational',     // Estudante R$ 29/mês
  //   '1234568': 'commercial',       // Pro Individual R$ 89/mês
  //   '1234569': 'pro_engineering',  // Pro Engenharia R$ 199/mês
};

export const TIER_VALIDITY_DAYS: Record<string, number> = {
  educational: 30,
  demo: 7,
  commercial: 30,
  pro_engineering: 30,
  enterprise: 365,
};

export const MAX_ACTIVATIONS_PER_KEY: Record<string, number> = {
  educational: 2,
  demo: 1,
  commercial: 3,
  pro_engineering: 5,
  enterprise: 100,
};

export const TIER_LABEL_PT: Record<string, string> = {
  educational: 'Estudante',
  demo: 'Demo',
  commercial: 'Pro Individual',
  pro_engineering: 'Pro Engenharia',
  enterprise: 'Empresarial',
};

export const JWT_VALIDITY_SECONDS = 30 * 86400; // 30 dias

// URL pública de download do bundle Pro (Cloudflare R2 / CDN)
// A ser preenchida após Sprint 3 (build dual gerado e hospedado)
export const DOWNLOAD_URL_PRO = 'https://releases.olivas.com.br/pro/latest';

// E-mail "from" do Resend (precisa domínio verificado em resend.com)
export const EMAIL_FROM = 'Olivas <licencas@olivas.com.br>';
