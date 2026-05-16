/**
 * Templates de e-mail transacional em português brasileiro.
 *
 * Conformidade LGPD: nenhum dado de terceiros é incluído além
 * do estritamente necessário para entrega do serviço.
 */

const BASE_STYLE = `
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
max-width: 600px;
color: #222;
line-height: 1.5;
`;

const KEY_STYLE = `
display: inline-block;
font-family: "Courier New", monospace;
font-size: 16px;
font-weight: bold;
background: #f4f4f4;
border: 1px solid #ccc;
padding: 12px 18px;
border-radius: 4px;
letter-spacing: 1px;
`;


export interface WelcomeEmailArgs {
  customerName: string;     // "Cliente" se vazio
  customerEmail: string;
  licenseKey: string;
  tier: string;             // "commercial", "pro_engineering", ...
  tierLabel: string;        // "Pro Individual", "Estudante", ...
  expiryDate: string;       // YYYY-MM-DD
  downloadUrl: string;      // CDN do .exe Pro
  maxActivations: number;
}

export function welcomeKeyEmail(args: WelcomeEmailArgs): {
  subject: string;
  html: string;
  text: string;
} {
  const name = args.customerName?.trim() || 'cliente';

  const subject =
    `Sua chave do Olivas Power System Studio — ${args.tierLabel}`;

  const html = `
<div style='${BASE_STYLE}'>
  <h1 style="color:#7E2BA8;">Bem-vindo(a) ao Olivas Power System Studio!</h1>

  <p>Olá, <strong>${name}</strong>,</p>

  <p>Sua compra foi confirmada. Aqui está sua chave de licença
  para o tier <strong>${args.tierLabel}</strong>:</p>

  <p style="text-align:center;">
    <span style="${KEY_STYLE}">${args.licenseKey}</span>
  </p>

  <h3>Como usar:</h3>
  <ol>
    <li>Baixe o instalador em:<br>
      <a href="${args.downloadUrl}">${args.downloadUrl}</a>
    </li>
    <li>Execute <code>OlivasPSS-Pro.exe</code></li>
    <li>No menu <strong>Ajuda → Ativar Licença...</strong>
    (atalho <kbd>Ctrl+L</kbd>), cole a chave acima e clique
    <strong>Ativar</strong>.</li>
  </ol>

  <h3>Detalhes da assinatura:</h3>
  <ul>
    <li><strong>Tier:</strong> ${args.tierLabel}</li>
    <li><strong>Válida até:</strong> ${args.expiryDate}</li>
    <li><strong>Máquinas autorizadas:</strong>
    até ${args.maxActivations} computadores</li>
  </ul>

  <p>Você pode liberar uma máquina autorizada via o botão
  <strong>Remover licença</strong> no mesmo diálogo de ativação,
  para reaproveitar a cota em outro computador.</p>

  <h3>Documentos:</h3>
  <ul>
    <li><a href="https://olivas.com.br/legal/EULA">EULA</a> —
    Acordo de Licença</li>
    <li><a href="https://olivas.com.br/legal/PRIVACY">Política
    de Privacidade (LGPD)</a></li>
    <li><a href="https://olivas.com.br/legal/TERMS">Termos de
    Uso</a></li>
  </ul>

  <p>Dúvidas: responda este e-mail ou contate
  <a href="mailto:suporte@olivas.com.br">suporte@olivas.com.br</a>.</p>

  <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
  <p style="color:#888; font-size: 12px;">
    Olivas Power System Studio · Software de análise elétrica auditável<br>
    Este e-mail foi enviado para ${args.customerEmail} em razão da
    sua compra. Você pode exercer direitos LGPD via
    <a href="mailto:dpo@olivas.com.br">dpo@olivas.com.br</a>.
  </p>
</div>
`.trim();

  const text = `Olá, ${name},

Sua compra do Olivas Power System Studio foi confirmada.

Chave de licença (${args.tierLabel}):

    ${args.licenseKey}

Como usar:
1. Baixe o instalador: ${args.downloadUrl}
2. Execute OlivasPSS-Pro.exe
3. Menu Ajuda > Ativar Licença (Ctrl+L), cole a chave e clique Ativar.

Detalhes:
- Tier: ${args.tierLabel}
- Válida até: ${args.expiryDate}
- Máquinas autorizadas: até ${args.maxActivations}

Documentos:
- EULA: https://olivas.com.br/legal/EULA
- Privacidade LGPD: https://olivas.com.br/legal/PRIVACY
- Termos de Uso: https://olivas.com.br/legal/TERMS

Dúvidas: suporte@olivas.com.br
LGPD: dpo@olivas.com.br
`.trim();

  return { subject, html, text };
}


export interface RevocationEmailArgs {
  customerName: string;
  customerEmail: string;
  tierLabel: string;
  reason: string;   // "cancelamento" | "estorno" | "chargeback" | "manual"
}

export function revocationEmail(args: RevocationEmailArgs): {
  subject: string;
  html: string;
  text: string;
} {
  const name = args.customerName?.trim() || 'cliente';

  const subject =
    `Licença Olivas Power System Studio encerrada — ${args.tierLabel}`;

  const html = `
<div style='${BASE_STYLE}'>
  <h2>Sua licença foi encerrada</h2>

  <p>Olá, <strong>${name}</strong>,</p>

  <p>Conforme registrado em nosso sistema, sua licença
  <strong>${args.tierLabel}</strong> do Olivas Power System
  Studio foi encerrada.</p>

  <p><strong>Motivo:</strong> ${args.reason}</p>

  <p>O software continuará funcionando até a expiração natural
  do token local (até 30 dias), após o que reverterá para o tier
  <code>educational</code>.</p>

  <p>Caso isso seja um engano ou deseje reativar, contate
  <a href="mailto:suporte@olivas.com.br">suporte@olivas.com.br</a>.</p>

  <p>Direitos LGPD: <a href="mailto:dpo@olivas.com.br">dpo@olivas.com.br</a></p>
</div>
`.trim();

  const text = `Olá, ${name},

Sua licença ${args.tierLabel} do Olivas Power System Studio foi encerrada.
Motivo: ${args.reason}

O software continuará funcionando até a expiração natural do token
local (até 30 dias). Após isso, reverte para tier educational.

Caso seja engano, contate suporte@olivas.com.br
LGPD: dpo@olivas.com.br
`.trim();

  return { subject, html, text };
}
