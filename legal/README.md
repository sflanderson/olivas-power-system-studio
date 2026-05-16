# Documentos Jurídicos — Olivas Power System Studio

> **AVISO IMPORTANTE:** os textos neste diretório são **modelos
> de referência** redigidos pela equipe de desenvolvimento.
> **Antes de uso comercial real**, devem ser revisados por
> advogado(a) com OAB ativa, especializado(a) em direito digital
> e proteção de dados. O autor do projeto declara expressamente
> que este material **não constitui consultoria jurídica** e que
> a responsabilidade pelo uso é exclusiva do operador comercial.

## Índice

| Documento | Quando aplicar |
|-----------|----------------|
| [EULA.md](EULA.md) | Acordo de Licença do Usuário Final — aceito ao instalar o binário Pro (Hotmart/ML) |
| [TERMS.md](TERMS.md) | Termos de Uso do serviço de licença (license server + atualizações) |
| [PRIVACY_LGPD.md](PRIVACY_LGPD.md) | Política de Privacidade conforme LGPD (Lei 13.709/2018) |
| [SLA.md](SLA.md) | Acordo de Nível de Serviço — apenas Pro Engenharia e Empresarial |
| [CLA.md](CLA.md) | Contributor License Agreement — para PRs externos no GitHub público |

## Edição Community vs Pro

| Aspecto | Community | Pro |
|---------|-----------|-----|
| **Licença do código-fonte** | Apache 2.0 (LICENSE.txt) | Apache 2.0 |
| **Licença do binário .exe** | Apache 2.0 | **EULA proprietária** (este diretório) |
| **Aceite obrigatório** | Não | Sim, na primeira execução do .exe Pro |
| **ToS de serviço** | Não aplicável | Sim, ao usar license server |
| **Privacy LGPD** | Não coleta dados | Sim, e-mail + machine_id + telemetry opt-in |

Por que dual licensing funciona:

* Código no GitHub é Apache 2.0 — qualquer um pode clonar, modificar,
  estudar, fazer fork. Não há custo nem permissão necessária.
* O binário Pro empacotado pela equipe oficial é distribuído como
  produto sob EULA. O Apache 2.0 não obriga distribuir binários
  derivados sob o mesmo formato — só obriga preservar copyright,
  NOTICE e disclaimer no código-fonte distribuído.
* Quem clona Apache 2.0 e cria seu próprio binário pode fazê-lo,
  mas não pode usar marca "Olivas", chaves do nosso license server,
  nem reutilizar templates premium, EULA, ou nosso logo.

## Como o aceite do EULA é registrado

Na primeira execução do binário **Pro**:

1. App detecta primeira execução (QSettings sem `eula/accepted_version`).
2. Mostra diálogo com texto integral de EULA + Termos.
3. Usuário marca "Li e aceito" + clica "Continuar".
4. App grava `eula/accepted_version=1.0` + `eula/accepted_at=<timestamp>`
   em QSettings.
5. Hash do texto aceito é incluído nos relatórios de audit trail
   (rastreabilidade da versão de termos em vigor no momento do laudo).

Na edição **Community**, esse fluxo não roda — o Apache 2.0
permite uso sem aceite prévio.

## Auditoria do controlador (LGPD)

| Função | Pessoa | Contato |
|--------|--------|---------|
| **Controlador** | Landerson Ferreira Silva (a ser substituído por CNPJ ME ao final do Sprint 4) | `dpo@olivas.com.br` (a configurar) |
| **Encarregado (DPO)** | Landerson Ferreira Silva | mesmo |
| **Suplente DPO** | a definir | — |

ANPD: pendente registro (não obrigatório para microempresa, mas
recomendado registrar incidentes se houver vazamento).

## Foro

Conforme cada documento — padrão: **Comarca de Belo Horizonte, MG**.

## Versão dos documentos

Todos os documentos carregam cabeçalho `Versão: 1.0.0` e
`Vigência: a partir de YYYY-MM-DD`. Mudanças devem ser registradas
em `legal/CHANGELOG.md` (a criar quando houver primeira revisão).

---

**Status atual:** modelos v1.0.0 redigidos no Sprint commercial-4
(2026-05-15). Não vigentes em produção até revisão jurídica.
