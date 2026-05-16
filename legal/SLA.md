# Acordo de Nível de Serviço — SLA

**Olivas Power System Studio — Pro Engenharia e Empresarial**

Versão: 1.0.0 · Vigência: a partir do aceite eletrônico

> ⚠ **AVISO**: este documento é um **modelo de referência** e
> ainda não foi revisado por advogado(a) habilitado(a) na OAB.

> Aplicável **apenas** aos tiers **Pro Engenharia** e
> **Empresarial**. Tier Estudante e Pro Individual seguem o
> suporte padrão dos [Termos de Uso](TERMS.md).

---

## 1. Métricas de disponibilidade

| Componente | Uptime alvo | Janela de medição |
|------------|-------------|-------------------|
| License server `/activate` | 99,9% | Mensal |
| License server `/refresh` | 99,5% | Mensal |
| License server `/health` | 99,9% | Mensal |
| Distribuição de atualizações (CDN) | 99,5% | Mensal |

**Exclusões da medição:**

- Janelas de manutenção programadas e comunicadas com 7 dias
  de antecedência (máx. 2h/mês);
- Indisponibilidade causada por **terceiros**
  (Cloudflare, Supabase, ISP do Licenciado);
- Força maior, caso fortuito, eventos de cibersegurança fora
  do controle razoável do Licenciante.

## 2. Suporte técnico

### 2.1 Canais

- **E-mail prioritário**: `support-pro@olivas.com.br`
  (a configurar)
- **WhatsApp Business** (somente Empresarial): número a
  divulgar após cadastro

### 2.2 Tempos de resposta inicial (SLO — Service Level Objective)

| Severidade | Definição | Pro Engenharia | Empresarial |
|------------|-----------|----------------|-------------|
| **S1 — Crítico** | Software ou license server indisponíveis impedindo trabalho | 4 horas úteis | 1 hora útil |
| **S2 — Alto** | Funcionalidade crítica com falha (audit trail, MC, PDF) | 1 dia útil | 4 horas úteis |
| **S3 — Médio** | Funcionalidade não-crítica, workaround disponível | 2 dias úteis | 1 dia útil |
| **S4 — Baixo** | Dúvida, sugestão, melhoria | 5 dias úteis | 3 dias úteis |

**Horário útil:** 09h–18h BRT, dias úteis (segunda a sexta).

### 2.3 Tempos de resolução-alvo (SLO, não-vinculantes)

| Severidade | Pro Engenharia | Empresarial |
|------------|----------------|-------------|
| S1 | 1 dia útil | 4 horas úteis |
| S2 | 5 dias úteis | 2 dias úteis |
| S3 | 30 dias | 15 dias |
| S4 | Backlog priorizado | Backlog priorizado |

## 3. Compensação por descumprimento

3.1. Caso a disponibilidade mensal real de `/activate` fique
abaixo do alvo:

| Disponibilidade real | Crédito (% mensalidade) |
|----------------------|--------------------------|
| 99,0% – 99,89% | 5% |
| 95,0% – 98,99% | 10% |
| < 95,0% | 25% |

Créditos são aplicados na próxima fatura. Apenas o Licenciado
pode reivindicar — envio de e-mail ao DPO no mês seguinte ao
incidente, com cálculo justificado.

3.2. Não há compensação automática por descumprimento de SLO
de resposta de suporte, mas reclamações reiteradas serão
escaladas formalmente.

## 4. Manutenção programada

4.1. Janelas preferenciais: **terça-feira, 02h–04h BRT**.

4.2. Comunicação: e-mail + post em `status.olivas.com.br`
(a configurar) com 7 dias de antecedência para janelas planejadas.

4.3. Emergências críticas (CVE crítica em deps): manutenção
imediata permitida com aviso por e-mail e log público.

## 5. Atualizações

| Tipo | Frequência alvo | Notificação |
|------|-----------------|-------------|
| **Patch** (4.x.y) | Conforme necessário | E-mail |
| **Minor** (4.y.0) | Trimestral | E-mail + release notes |
| **Major** (5.0.0) | Anual ou conforme roadmap | Comunicação prévia de 90 dias |

## 6. Excelência operacional

6.1. **Backups**: o banco do license server tem snapshots
diários retidos por 30 dias.

6.2. **DR (Disaster Recovery)**: RPO ≤ 24h, RTO ≤ 4h para
license server.

6.3. **Observabilidade**: métricas e logs estruturados
mantidos por 90 dias (license server).

## 7. Vigência e revisão

7.1. Este SLA vigora enquanto a assinatura Pro Engenharia ou
Empresarial estiver ativa.

7.2. Revisões anuais podem ajustar metas com aviso prévio de
60 dias.

## 8. Foro e lei aplicável

8.1. **Lei aplicável**: brasileira.

8.2. **Foro**: **Comarca de Belo Horizonte, MG**, ressalvado o
foro do domicílio do consumidor pessoa física, conforme regras
cogentes do CDC.

8.3. Este SLA é complementar ao [EULA](EULA.md) e aos
[Termos de Uso](TERMS.md), com os quais deve ser interpretado em
conjunto. Em caso de conflito, prevalece o documento mais
específico para a matéria em disputa.

---

**Versão deste SLA:** 1.0.0
**Data de redação:** 2026-05-15
**Status:** modelo pré-revisão jurídica
