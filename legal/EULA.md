# Acordo de Licença do Usuário Final — EULA

**Olivas Power System Studio — Edição Pro**

Versão: 1.0.0 · Vigência: a partir da data de aceite eletrônico
pelo Licenciado · Idioma de prevalência: **português brasileiro**

> ⚠ **AVISO**: este documento é um **modelo de referência** e
> ainda não foi revisado por advogado(a) habilitado(a) na OAB.
> Antes do uso comercial real, revise com profissional jurídico.

---

## 1. Definições

Para fins deste Acordo:

- **Software**: o binário "Olivas Power System Studio — Edição Pro"
  (OlivasPSS-Pro), incluindo seus módulos, bibliotecas embutidas,
  templates, catálogos, ícones e documentação eletrônica fornecida
  com o instalador.
- **Licenciante**: Landerson Ferreira Silva (CPF/CNPJ a constar
  na NFS-e), com sede em Belo Horizonte, MG, Brasil.
- **Licenciado**: pessoa física ou jurídica que adquiriu chave de
  licença do Software por meio dos canais autorizados
  (Hotmart, Mercado Livre, venda direta).
- **Chave de Licença**: string única no formato
  `OLV-<TIER>-<CUSTOMER>-<EXPIRY>-<HMAC>` emitida pelo Licenciante
  após confirmação do pagamento.
- **Máquina Autorizada**: computador individual no qual a Chave
  de Licença foi ativada, identificado por fingerprint anônima
  conforme [Política de Privacidade](PRIVACY_LGPD.md).
- **Período de Vigência**: prazo durante o qual a Chave de
  Licença é válida — mensal ou anual conforme plano contratado.

## 2. Concessão de licença

2.1. O Licenciante concede ao Licenciado, mediante pagamento
correspondente ao plano contratado, **licença não-exclusiva,
intransferível e revogável** para instalar e usar o Software
em até o número de Máquinas Autorizadas correspondente ao tier
adquirido:

| Tier | Máquinas Autorizadas máximas |
|------|------------------------------|
| Estudante | 2 |
| Pro Individual | 3 |
| Pro Engenharia | 5 |
| Empresarial | conforme contrato específico |

2.2. A licença permite uso **profissional e comercial** do
Software para elaboração de estudos elétricos, laudos técnicos,
projetos de instalações elétricas e documentação de auditoria
nos limites das normas técnicas referenciadas no manual do
Software.

2.3. A licença NÃO inclui:

a) Redistribuição do Software a terceiros, em qualquer meio,
   ainda que sem fins lucrativos;
b) Sublicenciamento;
c) Aluguel, leasing, hospedagem comercial multiusuário ou
   prestação de SaaS baseada no Software;
d) Uso em quantidade superior à de Máquinas Autorizadas do tier;
e) Engenharia reversa, descompilação, desofuscação ou tentativa
   de extrair código-fonte do binário Pro, exceto quando
   expressamente permitido por lei imperativa brasileira (e.g.
   Art. 6º, II, Lei 9.609/98);
f) Remoção ou alteração de avisos de copyright, marca ou
   atribuição embutidos no Software.

2.4. **Código-fonte Apache 2.0 disponível separadamente**: a
versão Community do Olivas Power System Studio é distribuída sob
Apache License 2.0 no repositório público oficial. Direitos sobre
o código-fonte são regidos por aquele acordo, NÃO por este EULA.
Este EULA aplica-se exclusivamente ao binário Pro e seus
artefatos proprietários.

## 3. Chave de Licença e Máquinas Autorizadas

3.1. A Chave de Licença é vinculada ao identificador do cliente
no canal de venda (Hotmart subscription ID ou pedido Mercado
Livre) e à(s) Máquina(s) Autorizada(s) ativadas. Cada ativação
consome uma cota do tier.

3.2. O Licenciado pode **liberar uma Máquina Autorizada** via
funcionalidade "Remover licença" do Software para reaproveitar
a cota em outro computador.

3.3. O Licenciante pode **revogar** a Chave de Licença nos casos
de:

a) Inadimplência (assinaturas recorrentes);
b) Estorno, chargeback ou reembolso solicitado;
c) Tentativa comprovada de fraude no sistema de licenciamento
   (compartilhamento massivo, engenharia reversa, etc);
d) Violação substancial deste EULA.

3.4. Em caso de revogação por violação, o Licenciado **não tem
direito a reembolso proporcional**.

3.5. Em caso de cancelamento dentro de **7 (sete) dias** da
compra, conforme **Art. 49 do Código de Defesa do Consumidor
(Lei 8.078/90)** para compras à distância, o reembolso é
integral e a chave é revogada.

## 4. Atualizações

4.1. Durante o Período de Vigência, o Licenciado tem direito a
todas as atualizações **minor** e **patch** do Software dentro
da mesma linha major (e.g. de v4.1.x para v4.5.x).

4.2. Atualizações **major** (e.g. v4 → v5) **podem requerer**
nova aquisição ou upgrade conforme política comercial vigente.

4.3. O Licenciante reserva-se o direito de alterar, sem aviso
prévio, recursos não essenciais (cores de UI, ordem de menus,
linguagem de mensagens), respeitando o conjunto de
funcionalidades centrais comprometidas no plano.

## 5. Garantia limitada e isenção de responsabilidade

5.1. **GARANTIA TÉCNICA LIMITADA**: o Licenciante garante que,
durante 30 (trinta) dias contados da ativação, o Software
executa as funções essenciais descritas em seu manual em
ambiente Windows 10/11 64-bit dentro dos requisitos mínimos
publicados. Caso o Software não atenda essa garantia, o
Licenciante providenciará, **a seu exclusivo critério**:
correção, substituição ou reembolso proporcional do valor pago.

5.2. **ISENÇÃO PROFISSIONAL — CRÍTICO**: o Software produz
laudos, relatórios e resultados de cálculo elétrico que são
**ferramentas de apoio à decisão**, não substituem o juízo
técnico de engenheiro(a) eletricista habilitado(a) (CREA
ativo). O Licenciado reconhece que:

a) Todo laudo gerado pelo Software deve ser **revisado,
   assinado e responsabilizado tecnicamente** por engenheiro(a)
   eletricista habilitado(a), conforme **NR-10 §10.2.4** e a
   legislação profissional aplicável;
b) Os **valores numéricos** calculados são aproximações
   conforme os modelos das normas IEC 60909, IEEE 1584, IEEE
   242, NBR 17227 etc, com as **limitações declaradas**
   automaticamente no rodapé de cada laudo;
c) O Software **não isenta** o engenheiro responsável de
   verificar os dados de entrada, a topologia adotada, as
   premissas de modelagem e a coerência dos resultados.

5.3. **EXCLUSÃO DE GARANTIAS IMPLÍCITAS**: salvo a garantia
expressa em 5.1, o Software é fornecido "**TAL COMO ESTÁ**".
O Licenciante isenta-se de garantias implícitas de
**comerciabilidade**, **adequação a propósito específico**,
**ininterrupção** ou **ausência de erros**.

## 6. Limitação de responsabilidade

6.1. Em nenhuma hipótese o Licenciante será responsável por
danos:

a) **Indiretos**, incidentais, consequenciais ou lucros
   cessantes;
b) Decorrentes de **decisões técnicas tomadas com base nos
   relatórios** do Software, conforme isenção da cláusula 5.2;
c) Decorrentes de **falhas em equipamentos físicos** elétricos
   alvo das análises, ainda que motivadas por dimensionamento
   incorreto baseado em laudo produzido com o Software;
d) Decorrentes de **interrupções do license server**, força
   maior ou caso fortuito.

6.2. A responsabilidade agregada total do Licenciante perante o
Licenciado, por qualquer motivo, fica limitada a **2 (duas) vezes**
o valor pago pelo Licenciado nos 12 (doze) meses anteriores ao
evento gerador.

6.3. Esta limitação não se aplica a danos decorrentes de **dolo
ou culpa grave** do Licenciante, nas hipóteses em que a lei
brasileira imperativa proíba a limitação.

## 7. Propriedade intelectual

7.1. O Software, sua marca, logos, código binário, layouts de
relatório, templates premium, biblioteca de relés/equipamentos
e documentação técnica são de **propriedade exclusiva do
Licenciante** e/ou licenciados de terceiros (PySide6/Qt sob
LGPL v3, matplotlib sob PSF, etc).

7.2. Avisos de terceiros estão consolidados em
[`docs/THIRD_PARTY_NOTICES.md`](../docs/THIRD_PARTY_NOTICES.md)
e devem ser preservados.

7.3. Marcas "Olivas", "Olivas Power System Studio" e logos
associados são marcas do Licenciante e não podem ser usadas
sem autorização escrita.

## 8. Suporte técnico

8.1. Tier **Estudante e Pro Individual**: suporte por e-mail,
prazo de resposta em até 5 dias úteis.

8.2. Tier **Pro Engenharia**: prazo de resposta em até 2 dias
úteis. Detalhes adicionais em [`SLA.md`](SLA.md).

8.3. Tier **Empresarial**: conforme contrato específico.

## 9. Proteção de dados (LGPD)

9.1. O tratamento de dados pessoais do Licenciado é regido
pela [Política de Privacidade](PRIVACY_LGPD.md), parte
integrante deste EULA.

9.2. Ao aceitar este EULA, o Licenciado declara ciência das
finalidades e bases legais de tratamento ali descritas.

## 10. Vigência e rescisão

10.1. Este EULA vigora a partir do aceite eletrônico e
permanece em vigor enquanto a Chave de Licença estiver válida
e não-revogada.

10.2. **Rescisão por descumprimento**: violação das cláusulas
2.3 ou 5 autoriza o Licenciante a revogar a Chave de Licença
e este EULA, sem prejuízo de medidas judiciais.

10.3. **Rescisão por conveniência**: o Licenciado pode
cancelar a assinatura a qualquer momento no canal de origem
(Hotmart, painel próprio). A revogação da Chave de Licença
ocorre ao final do período pago.

10.4. **Sobrevivência**: as cláusulas 5, 6, 7 e 11 sobrevivem
ao término deste EULA.

## 11. Disposições gerais

11.1. **Lei aplicável**: este EULA é regido pela **lei
brasileira**.

11.2. **Foro**: fica eleito o **Foro da Comarca de Belo
Horizonte, Estado de Minas Gerais**, com renúncia a qualquer
outro, por mais privilegiado que seja, para dirimir
controvérsias decorrentes deste Acordo, ressalvada a competência
prevista em norma cogente do CDC para foro do domicílio do
consumidor pessoa física.

11.3. **Aceite eletrônico**: o aceite via diálogo do Software
e/ou conclusão de compra no Hotmart/ML constituem manifestação
inequívoca de vontade, equivalente a assinatura nos termos do
Art. 10, §2º, da MP 2.200-2/2001.

11.4. **Mudanças**: alterações neste EULA serão comunicadas
por e-mail e publicação na pasta `legal/` do repositório
oficial. Continuação de uso após 30 dias da comunicação
equivale a aceite tácito.

11.5. **Idioma de prevalência**: em caso de tradução, a versão
em **português brasileiro** prevalece.

11.6. **Independência das cláusulas**: a invalidade de uma
cláusula não invalida as demais.

---

**Versão deste EULA:** 1.0.0
**Data de redação:** 2026-05-15
**Status:** modelo pré-revisão jurídica

Para dúvidas: `legal@olivas.com.br` (a configurar).
