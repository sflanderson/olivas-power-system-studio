# Termos de Uso — Olivas Power System Studio

**Termos de Uso do Serviço de Licenciamento e Atualizações**

Versão: 1.0.0 · Vigência: a partir da data de aceite eletrônico ·
Idioma de prevalência: **português brasileiro**

> ⚠ **AVISO**: este documento é um **modelo de referência** e
> ainda não foi revisado por advogado(a) habilitado(a) na OAB.
> Antes do uso comercial real, revise com profissional jurídico.

---

## 1. Aceite e escopo

1.1. Estes Termos de Uso ("Termos") regem a utilização do
**serviço de licenciamento, ativação e atualização** ("Serviço")
fornecido pelo Licenciante ao Licenciado em conexão com o
Olivas Power System Studio Edição Pro.

1.2. O aceite destes Termos ocorre **conjuntamente** com o
aceite do [EULA](EULA.md) ao primeiro uso da Chave de Licença.
Estes Termos são complementares e devem ser interpretados em
conjunto com o EULA.

## 2. Descrição do Serviço

2.1. O Serviço compreende:

a) **Servidor de licença** (`api.olivas.com.br/license`,
   provisionado em Cloudflare Workers) — recebe a Chave de
   Licença e o identificador anônimo da Máquina, retorna
   token de validação criptograficamente assinado (JWT RS256).
b) **Renovação automática de token** a cada 7–30 dias quando
   a Máquina Autorizada está online.
c) **Revogação remota** em caso de fraude, inadimplência ou
   cancelamento do plano.
d) **Distribuição de atualizações** via download a partir do
   canal oficial do Licenciante (`releases.olivas.com.br` ou
   equivalente em CDN).

2.2. O Serviço **não inclui**:

a) Processamento de dados elétricos do Licenciado em
   servidores remotos — toda computação ocorre **localmente**
   na Máquina Autorizada;
b) Backup de projetos do Licenciado — esses ficam exclusivamente
   na Máquina;
c) Hospedagem de relatórios gerados.

## 3. Conta e responsabilidades

3.1. **Identificação**: o Licenciado é identificado pelo
e-mail informado no canal de compra (Hotmart/ML) e por um
**customer_id** atribuído pelo Licenciante.

3.2. **Responsabilidade pela chave**: a Chave de Licença é
**pessoal e intransferível**. O Licenciado é responsável por
proteger sua chave contra acesso não autorizado de terceiros.

3.3. **Uso fraudulento ou abusivo**: o Licenciante pode
suspender o Serviço, sem aviso prévio, em casos de:

a) Compartilhamento da Chave de Licença em fóruns públicos
   ou plataformas piratas;
b) Tentativa de gerar chaves falsas, fazer downgrade
   intencional do tier ou contornar o license server;
c) Uso em mais máquinas que o limite do tier, após esgotamento
   de tentativas de regularização;
d) Carga anormal nos endpoints do Serviço caracterizando
   tentativa de DoS ou scraping massivo.

## 4. Disponibilidade e manutenção

4.1. **Uptime alvo**: o Licenciante busca disponibilidade
mensal de **99,5%** para o license server, considerando todos
os tiers. Métricas para tier Pro Engenharia e Empresarial
estão em [`SLA.md`](SLA.md).

4.2. **Janelas de manutenção**: até **2 horas/mês** em
horários de baixo tráfego (madrugada UTC-3), com aviso prévio
quando possível.

4.3. **Operação offline**: o Software continua funcional
**até a expiração natural do token JWT** (30 dias após última
renovação bem-sucedida) mesmo sem rede. Após esse prazo, o
tier reverte para `educational` até nova ativação.

4.4. **Indisponibilidade prolongada**: em caso de
indisponibilidade superior a 7 dias consecutivos, o
Licenciante poderá emitir tokens de extensão por canal
alternativo (e-mail com instruções de ativação offline).

## 5. Pagamento, cobrança e cancelamento

5.1. **Recorrência (Hotmart)**: planos mensais e anuais são
processados via Hotmart, que atua como intermediadora de
pagamento e responsável pelos meios de pagamento aceitos
(cartão, boleto, PIX). Reembolsos e disputas seguem as
políticas vigentes da Hotmart.

5.2. **Compra única (Mercado Livre)**: planos anuais
ofertados via ML são compras únicas que dão direito a 12
meses de Serviço a partir da data de ativação.

5.3. **Cancelamento pelo Licenciado**:

a) Recorrência: cancelar diretamente no painel Hotmart
   (`hotmart.com/account/subscriptions`). O Serviço permanece
   ativo até o fim do período pago.
b) Compra única: não há cancelamento após o período de 7 dias
   do CDC (Art. 49, Lei 8.078/90).

5.4. **Cancelamento pelo Licenciante**: em casos do item 3.3,
o Licenciante pode encerrar o Serviço com revogação imediata
da Chave de Licença.

5.5. **Reembolso por 7 dias do CDC**: pessoa física tem
direito a reembolso integral em até 7 dias da compra, com
revogação da chave.

## 6. Alterações no Serviço

6.1. O Licenciante pode alterar funcionalidades, endpoints,
limites de uso ou política de tiers, mediante aviso prévio
de **30 dias** ao Licenciado, por e-mail e na pasta `legal/`
do repositório oficial.

6.2. Alterações que reduzam materialmente o conjunto de
funcionalidades contratadas dão ao Licenciado direito a
cancelamento sem ônus, mediante notificação dentro de 30 dias
da comunicação.

## 7. Propriedade intelectual do Serviço

7.1. O código do license server, endpoints, esquemas de banco
de dados e métricas operacionais são de **propriedade
exclusiva do Licenciante** e regidos por estes Termos, não
pelo Apache 2.0 do código Community.

## 8. Confidencialidade

8.1. O Licenciante mantém confidencialidade sobre dados de
uso do Serviço, sujeitos apenas ao tratamento descrito em
[`PRIVACY_LGPD.md`](PRIVACY_LGPD.md).

8.2. O Licenciado mantém confidencialidade sobre eventuais
informações comerciais privilegiadas do Licenciante
(roadmap não-público, métricas internas, etc) que receba
em canais de suporte.

## 9. Disposições gerais

9.1. **Lei aplicável**: brasileira.

9.2. **Foro**: **Comarca de Belo Horizonte, MG**, ressalvado
foro do domicílio do consumidor pessoa física.

9.3. **Boas práticas Hotmart**: o Licenciado declara conhecer
e cumprir a [Política de Uso Responsável da Hotmart](https://hotmart.com/pt-br/legal/responsible-use-policy).

9.4. **Vigência indeterminada** enquanto houver assinatura
ativa.

---

**Versão destes Termos:** 1.0.0
**Data de redação:** 2026-05-15
**Status:** modelo pré-revisão jurídica
