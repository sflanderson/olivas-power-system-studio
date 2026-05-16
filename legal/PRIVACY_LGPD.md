# Política de Privacidade — LGPD

**Olivas Power System Studio**

Versão: 1.0.0 · Vigência: a partir da data de aceite eletrônico ·
Idioma de prevalência: **português brasileiro**

> ⚠ **AVISO**: este documento é um **modelo de referência** e
> ainda não foi revisado por advogado(a) habilitado(a) na OAB.
> Antes do uso comercial real, revise com profissional jurídico
> e/ou DPO certificado.

---

## 1. Identificação do controlador

| Campo | Valor |
|-------|-------|
| **Controlador** | Landerson Ferreira Silva (a ser substituído pelo CNPJ ME assim que constituído) |
| **Endereço** | Universidade Federal de Minas Gerais — Av. Antônio Carlos, 6627 — Belo Horizonte, MG (endereço fiscal substituirá após abertura ME) |
| **DPO / Encarregado** | Landerson Ferreira Silva (interim) |
| **Contato LGPD** | `dpo@olivas.com.br` (a configurar) |
| **Telefone** | a configurar |

## 2. Quais dados pessoais coletamos

### 2.1 Dados fornecidos pelo titular

| Dado | Quando | Origem |
|------|--------|--------|
| E-mail | No checkout Hotmart/ML | Hotmart/ML repassa via webhook |
| Nome completo (opcional) | No checkout, se cliente informa | Hotmart/ML |
| Documento (CPF/CNPJ) | Apenas Hotmart/ML — **não armazenamos** | Hotmart/ML processa pagamento |

### 2.2 Dados coletados automaticamente

| Dado | Quando | Finalidade |
|------|--------|------------|
| **Machine ID** (SHA256 hex de MAC+hostname+cpuid+platform) | Na ativação da Chave de Licença | Vincular ativação a máquina específica, prevenir compartilhamento |
| **Customer ID** (ID Hotmart ou pedido ML) | Na compra | Vincular Chave à compra para gestão de assinatura |
| **Eventos de telemetria (opt-in)** | Apenas se ativado em "Configurações → Privacidade" | Métricas agregadas anônimas de uso |
| **Logs do license server** | A cada chamada de `/activate`, `/refresh` | Auditoria de segurança, depuração |

### 2.3 Dados que NUNCA coletamos

- ❌ Dados elétricos dos projetos do Licenciado (ficam apenas
  na Máquina);
- ❌ Endereço IP residencial (Cloudflare descarta; armazenamos
  apenas o **país** derivado do IP para detecção de fraude);
- ❌ Senhas — nunca pedimos senha do Hotmart ou ML;
- ❌ Hostname real ou identificadores de hardware em texto claro
  — apenas o hash SHA256;
- ❌ Conteúdo de relatórios ou laudos gerados pelo Software;
- ❌ Histórico de navegação ou cookies de terceiros — o Software
  é desktop nativo, sem navegador embutido.

## 3. Finalidades e bases legais

Conforme **Art. 7 da Lei 13.709/2018 (LGPD)**:

| Finalidade | Base legal (Art. 7) | Dados envolvidos |
|------------|---------------------|------------------|
| Emitir Chave de Licença após compra | V — execução de contrato | E-mail, Customer ID |
| Vincular Chave à Máquina Autorizada | V — execução de contrato | Machine ID |
| Enviar atualizações e avisos de segurança | II — cumprimento de obrigação legal/regulatória; V — execução de contrato | E-mail |
| Comunicação promocional | I — consentimento (opt-in explícito) | E-mail |
| Telemetria de uso | I — consentimento (opt-in explícito) | Eventos anônimos |
| Auditoria de segurança e prevenção a fraude | IX — legítimo interesse | Logs de license server, país do IP |
| Cumprir solicitações de autoridades | VI — exercício regular de direitos | Conforme demanda formal |

## 4. Compartilhamento de dados

4.1. **Operadores contratados** (Art. 5, VII LGPD):

| Operador | O que processa | Finalidade |
|----------|---------------|------------|
| **Hotmart** | E-mail, dados de pagamento, subscription ID | Intermediação de pagamento e cobrança |
| **Mercado Livre** | E-mail, dados de pedido | Intermediação de venda única |
| **Cloudflare Workers** | Requests ao license server | Hospedagem do API gateway |
| **Supabase (Postgres BR)** | Chaves, ativações, e-mail | Banco de dados das licenças |
| **Resend** | E-mail | Envio de e-mail transacional (entrega de chave + avisos) |

Cada operador tem contrato com cláusulas LGPD/GDPR compatíveis.

4.2. **NÃO vendemos** dados pessoais a terceiros. NÃO compartilhamos
para marketing de parceiros sem consentimento específico.

4.3. **Transferência internacional**: Cloudflare e Supabase
podem replicar dados em regiões fora do Brasil (Cloudflare é
edge-global; Supabase oferece região São Paulo, **preferida** e
configurada para este projeto). Quando ocorrer transferência,
seguimos as garantias do **Art. 33 LGPD**, dando preferência a
operadores com certificações reconhecidas pela ANPD.

## 5. Tempo de retenção

| Dado | Retenção |
|------|----------|
| Chave de Licença ativa | Enquanto vigente + 5 anos após expiração (prazo prescricional CDC) |
| Logs de ativação | 12 meses |
| Logs do license server (técnicos) | 90 dias |
| E-mail de marketing | Até revogação do consentimento |
| Eventos de telemetria | 24 meses, agregados após 6 meses |

Após o prazo, dados são **eliminados ou anonimizados**.

## 6. Direitos do titular (Art. 18 LGPD)

O Licenciado tem direito a:

| # | Direito | Como exercer |
|---|---------|--------------|
| I | Confirmar tratamento | E-mail ao DPO |
| II | Acessar os dados | E-mail ao DPO; resposta em até 15 dias |
| III | Corrigir dados | E-mail ao DPO ou painel próprio |
| IV | Anonimizar, bloquear ou eliminar dados desnecessários ou tratados em desconformidade | E-mail ao DPO |
| V | Portabilidade | E-mail ao DPO; entrega em formato estruturado |
| VI | Eliminar dados tratados com consentimento | E-mail ao DPO; pode encerrar funcionalidade vinculada |
| VII | Informações sobre compartilhamento | Consultar esta política, seção 4 |
| VIII | Informações sobre não-consentimento | Consultar esta política, seção 8 |
| IX | Revogar consentimento | E-mail ao DPO ou opt-out em "Configurações → Privacidade" |

Canal preferencial: `dpo@olivas.com.br` (a configurar). Resposta
em até **15 dias úteis**.

## 7. Segurança

7.1. Medidas técnicas e organizacionais:

- **HMAC SHA256** para integridade da Chave de Licença
- **JWT RS256** (chave assimétrica) para tokens de validação
- **TLS 1.3** obrigatório em todos endpoints
- **Row-Level Security (RLS)** no Supabase — apenas service
  role do Worker acessa
- **Rate limiting** (100 req/min por IP) para endpoints públicos
- **Segredos** (`HMAC_SECRET`, `JWT_PRIVATE_KEY`, `SUPABASE_SERVICE_KEY`)
  armazenados em Cloudflare Secrets, nunca em código
- **Telemetria opt-in por padrão off** (Art. 7, I — consentimento
  inequívoco)

7.2. **Notificação de incidentes**: incidentes que possam
acarretar risco aos titulares serão comunicados à **ANPD** e
aos titulares afetados em **prazo razoável** (referência: 2 dias
úteis), conforme **Art. 48 LGPD**.

## 8. Cookies e armazenamento local

8.1. O Software é uma **aplicação desktop nativa** sem
navegador embutido. Não usa cookies HTTP.

8.2. **Armazenamento local** via `QSettings` do Qt e arquivos
em `%APPDATA%/OlivasATPStudio` (Windows) ou `~/.olivas_atp_studio`
(Linux/macOS):

| Arquivo | Conteúdo | Propósito |
|---------|----------|-----------|
| QSettings `commercial/machine_id` | Hash SHA256 anônimo | Anti-pirataria |
| QSettings `commercial/license_token` | JWT da licença ativa | Funcionamento offline |
| QSettings `commercial/license_tier` | Tier atual | UI gating |
| Diretório `runs/` | Outputs de simulação local | Histórico do usuário |
| Diretório `auto-save/` | Backup automático de projetos abertos | Crash recovery |

Tudo isso fica **apenas na máquina** e não é enviado a nenhum
servidor (exceto `machine_id`, que é enviado ao license server
apenas em formato hash).

## 9. Crianças e adolescentes (Art. 14 LGPD)

9.1. O Software **não é destinado** a menores de 18 anos. Não
coletamos intencionalmente dados de crianças ou adolescentes.

9.2. Caso identifiquemos coleta indevida, eliminaremos os dados
em até 5 dias úteis.

## 10. Alterações nesta política

10.1. Mudanças materiais serão comunicadas por e-mail e
publicadas neste repositório (`legal/PRIVACY_LGPD.md`) com
data de versão atualizada.

10.2. Continuação de uso após 30 dias da comunicação equivale
a aceite tácito.

## 11. Foro e lei aplicável

11.1. **Lei aplicável**: brasileira, com primazia da
**LGPD (Lei 13.709/2018)** sobre cláusulas que com ela
conflitem.

11.2. **Foro**: **Comarca de Belo Horizonte, MG**, ressalvado
foro do domicílio do consumidor pessoa física.

## 12. Contato com o DPO e ANPD

- DPO Olivas: `dpo@olivas.com.br` (a configurar)
- ANPD: <https://www.gov.br/anpd/pt-br>

---

**Versão desta Política:** 1.0.0
**Data de redação:** 2026-05-15
**Status:** modelo pré-revisão jurídica
