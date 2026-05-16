/**
 * Cliente mínimo do Resend para envio de e-mail transacional.
 *
 * Resend API docs: https://resend.com/docs/api-reference
 *
 * Limite free tier: 100 e-mails/dia, 3 000/mês — suficiente
 * para o primeiro semestre de soft launch.
 */

export interface ResendClient {
  apiKey: string;
  from: string;
}

export function createResendClient(apiKey: string, from: string): ResendClient {
  return { apiKey, from };
}

interface SendArgs {
  to: string;
  subject: string;
  html: string;
  text: string;
  reply_to?: string;
  tags?: Array<{ name: string; value: string }>;
}

export async function sendEmail(
  client: ResendClient,
  args: SendArgs,
): Promise<{ id: string }> {
  const resp = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${client.apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: client.from,
      to: [args.to],
      subject: args.subject,
      html: args.html,
      text: args.text,
      reply_to: args.reply_to,
      tags: args.tags,
    }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Resend ${resp.status}: ${text}`);
  }

  return (await resp.json()) as { id: string };
}
