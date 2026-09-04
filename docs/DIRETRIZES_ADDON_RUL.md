# Diretrizes de construção — Add-on de RUL de Isolação de Estator

**Para:** o agente que vai integrar o módulo ao Olivas Power System Studio.
**Base:** branch `claude/isolamento-degradacao-monitoramento-dr900x`.
**Versão-alvo:** **v4.2.0**. A árvore está em `4.0.0-beta` (`app/core/version.py:1959-1960`, `VERSION_TUPLE = (4, 0, 0)` e `PRE_RELEASE = "beta"`; entrada mais recente do `CHANGELOG.md:7` é `[4.0.0-beta] — 2026-05-01`). O número é fixado aqui porque dele dependem o nome do ponto de restauração, o nome do audit de abertura, a entrada do CHANGELOG e os nomes dos arquivos de teste — que já foram escolhidos como `test_pp_v4_2_0_*`.
**Estatuto deste documento:** substitui `docs/HANDOFF_MODULO_RUL_ISOLAMENTO.md` como instrução de trabalho. O handoff continua útil como narrativa técnica, mas contém erros de contagem e de procedência que estão corrigidos abaixo, um a um, com o comando que os refuta.

Convenção de verificação: tudo que este documento afirma sobre o repositório foi executado ou lido nesta sessão, na árvore de trabalho da branch acima, e vem com arquivo e linha. O que **não** foi verificado está marcado como tal em §8.

---

## 1. O que é o módulo e o que ele entrega

O módulo responde a uma pergunta que o Olivas hoje não responde: **quantas manobras do disjuntor a vácuo a isolação do estator deste motor de média tensão ainda suporta?** Ele o faz por dois caminhos separados e **não somáveis**:

* **Envelhecimento** — acúmulo de dano por regra de Miner sobre o perfil de estresse de cada excursão (`app/postprocessor/prognosis/damage_models.py`, acumulador em `:751`);
* **Travessia do envelope normativo** — evento terminal quando a forma de onda cruza o envelope da IEC 60034-15 (`app/simulation/emt/flashover.py:114`, `iec_60034_15_levels`).

O entregável é o **mínimo dos dois**, com o caminho dominante identificado: `SwitchingCampaign.life_summary` (`app/postprocessor/prognosis/switching_campaign.py:398`).

O gerador de estresse é um motor de transitórios eletromagnéticos **próprio**, em Python, sem binário de terceiro: kernel de Dommel, MNA, CDA de Lin e Martí, linhas Bergeron e JMarti, VCB dinâmico, snubber a tiristor, não linearidades por compensação (Dommel 1971), para-raios ZnO e disrupção de isolação.

### 1.0 Vocabulário obrigatório — o que "travessia" significa e o que ela não significa

Antes de qualquer número. O módulo declara, em `app/simulation/emt/flashover.py:479`, a chave `emt_flashover_withstand_is_not_breakdown`:

> "O limiar é um nível de SUPORTABILIDADE DE ENSAIO da IEC 60034-15, não a tensão de ruptura da máquina. A ruptura real ocorre ACIMA do nível de ensaio, por margem não publicada. O ramo, portanto, NÃO prevê o instante físico da disrupção."

Consequência que vale para tela, laudo, tooltip e log: **a contagem é contada; a interpretação da contagem como falha não é**. O vocabulário permitido é "travessia do envelope de ensaio da IEC 60034-15". As palavras "falha", "ruptura" e "fim de vida" só aparecem qualificadas — "fim de vida **pelo critério de ensaio**". Essa chave é obrigatória no bloco de limitações de toda saída que exiba `manobras_terminais`, `taxa_de_travessia` ou `manobras_ate_travessia` (Sprint 9, critério 2).

Segunda chave da mesma família, `emt_flashover_clamped_waveform_is_not_a_result` (mesma linha): quando o caminho de disrupção está ativo a forma de onda é grampeada, com ultrapassagem medida de 1,04 a 1,87 vez o limiar, e "o pico grampeado NÃO é, portanto, resultado quantitativo: o que o ramo entrega é a CONTAGEM de travessias e o instante de cada uma". Do cenário `literatura|disrupcao` **não se cita pico**; citam-se `fracao_com_disrupcao = 0.05333333333333334` e `disrupcoes_max = 16` (`varredura_vcb_n150_dt200ns.json`, bloco `resumo`).

### 1.1 As três camadas de certeza — e por que elas não podem partilhar o mesmo painel

Este é o ponto de produto mais importante do documento. As três lentes convergiram nele, e o próprio handoff o adverte na §4.2 **e o viola na §4.1**. As grandezas abaixo têm estatuto epistêmico diferente e **não podem ser renderizadas com a mesma tipografia**.

#### Camada CONTADA — pode ir a laudo como número, com o vocabulário da §1.0

| Grandeza | Valor | Procedência (verificada) |
|---|---|---|
| Travessias do envelope de ensaio, sem mitigação | **8 em 150 manobras** | `campanha_rul_n150.json` → `resumo.sem_mitigacao.manobras_terminais = 8` |
| Taxa de travessia (estimador uniforme) | **5,333 %** | mesmo arquivo, `taxa_de_travessia = 0.05333333333333334` |
| Manobras até a primeira travessia | **18,75** | mesmo arquivo, `manobras_ate_travessia = 18.75` |
| Manobras até a primeira travessia, **cota inferior a 95 %** | **11,20** | mesmo arquivo, `manobras_ate_travessia_cota_inferior = 11.199162055251845` |
| Travessias com para-raios | **0 em 150** | `resumo.com_para_raios.manobras_terminais = 0` |
| Cota inferior com para-raios | **> 50 manobras**, $p \le 2\,\%$ (95 %) | `manobras_ate_travessia_cota_inferior = 50.0`, regra de três (`RULE_OF_THREE = 3.0`, exposto em `app/postprocessor/prognosis/__init__.py`; conferido em runtime) |
| Fim de vida pelo critério de ensaio, caminho dominante | sem mitigação: **18,75** (travessia domina); com para-raios: **1,4374·10⁶** (envelhecimento domina) | `manobras_ate_o_fim` e `caminho_dominante` no mesmo `resumo` |

**A cota inferior de 11,20 é obrigatória ao lado de 18,75.** Citar 18,75 sozinho subestima o caso adverso em cerca de 40 %, e é a mesma classe de erro que este documento corrige no handoff.

**Correção obrigatória ao handoff §4.1.** Ele apresenta, na mesma lista e ambos como "calibrado", `p = 4,1 % ± 1,3 %` ("uma manobra em 24") e `18,75 manobras`. **São estimadores diferentes sobre a mesma amostra**: 18,75 = 1/(8/150) é a contagem uniforme, que é o que a campanha produz hoje; 4,134 % ± 1,319 % é o estimador **pós-estratificado**.

Estado exato do pós-estratificado, para que o Sprint 6 seja dimensionado certo: **o estimador existe em código e produz esse par**. `stratified_rate` (`app/simulation/emt/vcb_scenarios.py:969`) implementa literalmente $p = \sum W_h p_h$ e $\mathrm{Var}(p) = \sum W_h^2 p_h(1-p_h)/n_h$ (docstring em `:972-974`), sobre os estratos de `escalation_strata` (`:860`). Executado nesta sessão:

```
stratified_rate(escalation_strata(), crossings=(0, 8), counts=(107, 43))
→ (0.04134366925064599, 0.01318754086830859)
```

com estratos `(5,0; 40,0) kV/ms, W = 0,7778` e `(40,0; 50,0) kV/ms, W = 0,2222`. A partição 0/107 e 8/43 é a declarada em `docs/research/rul_isolamento/11_REDUCAO_DAS_LIMITACOES.md` l. 130-131 ("as oito travessias têm RRDS de polo condutor entre 40,7 e 48,3 kV/ms, todas no estrato alto. O estrato baixo dá 0 em 107"), e os valores conferem com a tabela de l. 136 e o refinamento de l. 148.

O que **não** existe é a ligação: `life_summary` (`switching_campaign.py:398`) devolve só a taxa uniforme, nenhum dos sete JSON grava o par (p, sd) estratificado, e `campanha_rul_n150.json` não registra por manobra o estrato a que ela pertence. O JSON de referência traz literalmente `descricao_da_taxa = "8 travessias em 150 manobras: p = 5.3% (<= 8.9% a 95 %), 18.8 manobras esperadas até a primeira"`.

Decisão adotada: o estimador pós-estratificado é o correto para citar (menor variância, não tendencioso sobre os mesmos dados), **mas só depois de ligado à campanha e rotulado** — é o Sprint 6, que é trabalho de *wiring* e de rotulagem de estrato, não de implementação de estimador. Até lá, o número citável é 5,3 % / 18,75 / 11,20, e nunca dois estimadores juntos sem rótulo.

#### Camada PROPAGADA — nunca sai sem a faixa

| Grandeza | Valor | Procedência |
|---|---|---|
| Manobras por envelhecimento, sem mitigação | **8,7801·10⁶** | `campanha_rul_n150.json` → `manobras_por_envelhecimento = 8780114.820168754` |
| Manobras por envelhecimento, com para-raios | **1,4374·10⁶** | mesmo bloco, `1437362.395920339` |
| Dispersão ao varrer o expoente da lei de potência inversa | fator **2,92·10³** na faixa (3,8; 11,7) | `docs/research/rul_isolamento/11_REDUCAO_DAS_LIMITACOES.md` l. 68 (tabela; l. 76 e l. 158 arredondam para 2,9·10³); faixa confirmada em runtime: `app.postprocessor.prognosis.IPL_EXPONENT_LITERATURE_RANGE == (3.8, 11.7)` |
| Asset Health Index | herda a mesma incerteza | `app/postprocessor/prognosis/health_index.py:273` |
| `CombinedDamageAccumulator.rul_years` | herda a mesma incerteza | `app/postprocessor/prognosis/damage_models.py:1071` |
| `EkfRulEstimator.predict_rul` | herda a mesma incerteza | `app/postprocessor/prognosis/rul_estimator.py:419` |

O próprio módulo declara isso: a chave `rul_params_not_calibrated` está em `app/postprocessor/prognosis/__init__.py:185` e a cota inferior de dano em `:194` (`rul_synergy_lower_bound`); o JSON traz `dano_e_cota_inferior: true` nas duas configurações.

#### Camada DECISÃO — livre de calibração, e é o argumento de venda

A **decisão** de mitigar não depende dos parâmetros não calibrados: quando o caminho terminal domina, a vida é $1/p$ e o expoente não entra na conta (dispersão exatamente 1). `exponent_robustness` (`app/postprocessor/prognosis/switching_campaign.py:860`) recomputa isso sobre perfis já simulados, sem simular nada, e `ExponentRobustness` (`:807`), método `describe()` (`:844`), devolve a frase pronta. É isto que o painel deve dizer ao decisor: **a recomendação é robusta; o prazo não é.**

### 1.2 Números do handoff que estão errados — não repita nenhum

Verifiquei os três JSON envolvidos. As correções:

* **"Pico cai de 77,5 para 3,45 pu"** — é comparação entre passos de integração diferentes. `77,52670888760886` é o máximo de `literatura|sem_snubber` em `varredura_vcb_n150.json`, cuja `configuracao` **não tem `dt_s`** e é o conjunto histórico a Δt = 1 µs; `3,448549528344089` é o máximo de `literatura|para_raios` em `varredura_vcb_n150_dt200ns.json`, cuja `configuracao` traz `"dt_s": 2e-07`. **No mesmo Δt = 0,2 µs o par é 76,898 → 3,449 pu.**
* **"Reignições, de 128 para 6"** — 128 é o máximo a 1 µs (`literatura|sem_snubber`, `reignicoes_totais.max`). A 0,2 µs os máximos são **191 (sem mitigação) → 7 (para-raios)**.
* **"O pico"** tem dois valores citáveis conforme a mitigação, no mesmo Δt = 0,2 µs: **76,90 pu** sem mitigação e **3,45 pu** com para-raios. Fixe um e diga qual. **O cenário `literatura|disrupcao` não entra nessa lista**: seu máximo de 13,134 pu é forma de onda grampeada, e a chave `emt_flashover_clamped_waveform_is_not_a_result` proíbe citá-lo como pico (§1.0). Desse cenário citam-se `fracao_com_disrupcao = 0,05333…` e `disrupcoes_max = 16`.
* **"O para-raios aumenta o dano em 4,3×"** — esse número vem da campanha de 60 manobras e o próprio `10_CAMPANHA_DOIS_CAMINHOS_DE_FIM_DE_VIDA.md` §3 se declara superado. Sobre `campanha_rul_n150.json`, **o fator correto é 6,11× por manobra de envelhecimento**: os danos totais estão sobre denominadores diferentes — `sem_mitigacao.manobras_de_envelhecimento = 142` contra `com_para_raios.manobras_de_envelhecimento = 150`. Por manobra, $(1{,}0436\cdot10^{-4}/150)\,/\,(1{,}6173\cdot10^{-5}/142) = 6{,}1085$, que é exatamente a razão $8780114{,}820168754 / 1437362{,}395920339$ que o próprio módulo calcula. A razão de totais, 6,45×, só pode ser citada com o rótulo "total sobre denominadores diferentes".
* **"72 limitações declaradas"** (handoff §5, l. 103) — são **87** chaves distintas. Contagem em runtime, por módulo: fachada `emt` 19, fachada `prognosis` 15, `vcb` 14, `snubber` 11, `motor_switching` 8, `atp_reference` 7, `jmarti` 7 (`JMARTI_LIMITATIONS`), `flashover` 6, `nonlinear` 4, `arrester` 3, `switching_campaign` 3 → **união de 87**.
* **"Onze documentos"** (handoff §9, l. 166) — `ls docs/research/rul_isolamento/*.md | wc -l` devolve **12**.
* **"196 s de suíte"** (handoff §2, l. 35) — não reproduzido nesta sessão (ver §8).

---

## 2. O que está no pacote

### 2.1 Código de produção — 21.861 linhas, 25 arquivos, hoje órfãs

| Pacote | Linhas (medidas) | Papel |
|---|---|---|
| `app/simulation/emt/` | **16.784** (`find … \| xargs wc -l`) | kernel de Dommel, MNA, CDA, Bergeron, JMarti, VCB, snubber, compensação, ZnO, disrupção |
| `app/postprocessor/prognosis/` | **4.235** | perfil de estresse, D1–D7, RUL por EKF, AHI, campanha |
| `scripts/` (3 arquivos) | 842 | `campanha_rul.py`, `varredura_vcb.py`, `varredura_rrds.py` |

As somas de 16.784 e 4.235 do handoff §2 **conferem**.

**Direção de dependência — já é a correta, e precisa ser congelada, não inventada.** `grep` em `app/postprocessor/prognosis/` por `from app.simulation` devolve vazio: o prognóstico **não importa** o motor EMT. O motor toca o prognóstico em **um único ponto de runtime e por import tardio dentro de função**: `app/simulation/emt/probes.py:275`, `from app.postprocessor.prognosis.stress_profile import extract_stress_events`, dentro de `to_stress_profile`. Existe um segundo contato, **em nível de módulo mas sob `if TYPE_CHECKING:`** (`probes.py:47-50`, `from app.postprocessor.prognosis.stress_profile import StressProfile`), que não executa. Essas são as únicas duas costuras entre as metades, e a trava do Sprint 11 tem de conhecer as duas.

**Fachadas incompletas — importa para o gate e para o laudo.** `app/simulation/emt/__init__.py:216` reexporta apenas `circuit`, `components`, `steady_state`, `line`, `jmarti` e `probes`. **Não** reexporta `vcb`, `vcb_scenarios`, `snubber`, `arrester`, `flashover` nem `nonlinear` — que é justamente por onde os três scripts importam. Consequência medida em runtime: a união dos catálogos das duas fachadas (`app/simulation/emt/__init__.py:311` + `app/postprocessor/prognosis/__init__.py:184`) dá **34** das 87 chaves. **53 chaves de auditoria não chegariam a laudo nenhum** montado a partir das fachadas.

**Sem `__all__` em quatro arquivos:** `stress_profile.py`, `damage_models.py`, `rul_estimator.py`, `health_index.py`. A superfície pública deles é definida de facto pelo `from … import` de `app/postprocessor/prognosis/__init__.py:79-128`.

**Superfícies públicas que o plano trata explicitamente, para que nenhuma fique órfã de rótulo:** `EkfRulEstimator` (`rul_estimator.py:177`), `predict_rul` (`:419`), `rul_from_damage` (`:530`), `CombinedDamageAccumulator.rul_years` (`damage_models.py:1071`), `PeakDistribution` (`switching_campaign.py:508`), `SurvivalCurve` (`:613`) e `survival` (`:691`) — todas reexportadas por `prognosis/__init__.py:130`. Ver Sprints 5, 8 e §3.4.

### 2.2 Documentação — 12 arquivos em `docs/research/rul_isolamento/`

Comece por `00_INDICE.md` (sistema de rótulos de evidência, §2.7; equações-âncora, §2.8) **sabendo que todas as contagens de código dele estão vencidas**: a §3.8 declara `app/simulation/emt/` com 11 arquivos / 9.915 linhas, `vcb.py` 1.115 l., `snubber.py` 684 l., `app/postprocessor/prognosis/` com 5 arquivos / 3.240 l., 449 testes em 62,66 s e catálogo de 41 chaves (19 alcançáveis). Medido nesta sessão: 16 arquivos / 16.784 l., `vcb.py` 2.480 l., `snubber.py` 1.102 l., 6 arquivos / 4.235 l., 829 testes coletados, 87 chaves (34 nas fachadas). O `00_INDICE.md` entra na lista de datação do Sprint 11.

Para a integração, os que importam:

* `05_MOTOR_EMT_DEDICADO.md` §11 — ponte com o prognóstico, lacuna do `.atp`, estado de órfão.
* `06_CASO_BASE_ATP_ESPECIFICACAO.md` — parâmetros decodificados do arquivo ATP, e a §4 com os itens que continuam indeterminados por falta da seção 5.3 do manual de referência do ATP (l. 76-82).
* `07_AUDITORIA_DO_CASO_ATP.md` — os dois defeitos do MODEL do arquivo que tornam a escalada impossível nele.
* `08` a `11` — a linha de validação. **`10` traz avisos de supersessão explícitos** (l. 56, "**Superado.**"; l. 73, "**Números superados.**"); **`08` traz ressalvas de escopo, não de supersessão** (l. 83, "**Valor convergido.**"; l. 136, "**Ressalva acrescentada depois.**"; l. 215, "**Estado.**"). `09` e `11` são os vigentes.
* **`04_ARQUITETURA_MVP_RUL_OLIVAS.md` está desatualizado por medição:** declara 3.052 linhas de `prognosis` (`04:3` e `04:458`) e 11 chaves de fachada (`04:13` e `04:163`), contra 4.235 e 15 medidas hoje. O `00_INDICE.md` §3.8 l. 388 já registrava a divergência — com um número que também envelheceu (3.240). Use o documento 04 para os *nomes* dos contratos C1–C4, nunca para contagens de código.

### 2.3 Dados — 7 JSON em `docs/research/rul_isolamento/anexos/dados/`

Todos com bloco `configuracao` reprodutível. O de `campanha_rul_n150.json` é literalmente:
`{"n": 150, "seed": 20260903, "dt_s": 2e-07, "envelope_V": 21640.0, "v_base_V": 3396.6257766593408, "limiar_deteccao_kV": 5.0, "impedancia_de_surto_ohm": 46.99}`.

| Arquivo | Estatuto |
|---|---|
| `campanha_rul_n150.json` | **Referência da cadeia completa.** 300 manobras (2 configurações × 150), Δt = 0,2 µs |
| `varredura_vcb_n150_dt200ns.json` | **Referência da varredura.** Δt = 0,2 µs, 3 mitigações × 150 |
| `varredura_vcb_n150.json` | Histórico a Δt = 1 µs. **Não produzir número novo daqui** |
| `campanha_rul_n60.json` | Histórico; números de envelhecimento superados |
| `varredura_rrds_*.json` (3) | Critério de aceitação de Wong, forma da dependência com a RRDS |

**O que `campanha_rul_n150.json` NÃO carrega, e que é insumo de dois sprints:** cada entrada de `manobras` tem exatamente as chaves `indice`, `com_para_raios`, `pico_pu`, `reignicoes`, `atravessou_envelope` e `perfis` (lido em runtime). Não há parâmetro de amostra do VCB — nem RRDS, nem corte, nem di/dt, nem tempo de arco. Só `varredura_vcb_n150_dt200ns.json` guarda `rrds_kV_por_ms`, e por fase, sem marcar qual polo conduz por último. Isso condiciona o Sprint 5 (o contrato v1 tem de carregar a amostra, ou o Sprint 6 não fecha) e o Sprint 6 (de onde vem o rótulo de estrato).

**Defeito de serialização a corrigir:** `resumo.com_para_raios.manobras_ate_travessia` é `Infinity` no JSON, o que **não é JSON válido**. `json.dumps(d["resumo"], allow_nan=False)` levanta `ValueError`. Qualquer consumidor estrito quebra.

---

## 3. Decisão de gate

**DUAS features. E o degrau entre elas não precisa de mecanismo novo.**

```python
# app/commercial/feature_gates.py, class Feature (:67-80)
EMT_SWITCHING_STUDY = "emt_switching_study"
RUL_INSULATION      = "rul_insulation"

# FEATURE_TIER_MAP (:84-96)
Feature.EMT_SWITCHING_STUDY: "pro_engineering",
Feature.RUL_INSULATION:      "enterprise",
```

### 3.1 O fato que muda a urgência, e que o handoff não menciona

`is_feature_available` (`app/commercial/feature_gates.py:211`) devolve **`True` para feature não catalogada** — o comentário no corpo diz "não bloquear features que ainda não foram comercializadas" — e `require_feature` (`:227`) retorna em silêncio no mesmo caso. Hoje o módulo **não está mal gateado: está sem gate, e por default aberto**, inclusive no bundle Community, cujo `build/runtime_hook_community.py` apenas força `OLIVAS_BUILD_EDITION=community` → tier `educational` (`current_tier`, `:156`). Catalogar não é polimento; é a diferença entre haver e não haver controle.

### 3.2 Por que `enterprise` para o RUL

Concordo com o destino do handoff §5, mas reordeno os argumentos e corrijo uma referência.

1. **O enquadramento contratual das limitações é a razão decisiva.** A saída de envelhecimento é declaradamente não calibrada pelo próprio módulo (`prognosis/__init__.py:185`) e o dano é cota inferior (`:194`). Vender isso por checkout automático, sem contrato e sem SLA, é o cenário em que as 87 limitações viram letra morta. `enterprise` é o único tier de venda direta com NFS-e e SLA.
2. **É decisão de capital, não cálculo de projeto** — "instale para-raios ou troque o motor em N manobras", com custo de indisponibilidade associado.
3. **Coerência do tier.** Hoje `enterprise` é composto só de features de *distribuição* — `MULTI_SEAT`, `WHITE_LABEL`, `ETAP_SKM_IMPORTER` (`feature_gates.py:93-95`). Não tem uma única razão **analítica** para existir. O RUL é a primeira.

**Correção ao handoff §5:** ele atribui multi-seat, white-label e importador ETAP/SKM à "§3" de `docs/MONETIZATION_PLAN.md`. A tabela §3 lista apenas `Multi-seat / multi-user | Empresarial`; white-label e importador estão na tabela de tiers da §2. O gate real — que é o que vale — está em `feature_gates.py:93-95`. Para referência ao longo deste plano: são **11** features catalogadas hoje, de `AUDIT_TRAIL_SHA256` (`:70`) a `ETAP_SKM_IMPORTER` (`:80`).

**Onde discordo do handoff:** a razão "exige dado de ativo" não é razão de tier, é **pré-condição de dado**. Tier resolve quem paga; não resolve o que a tela mostra a quem pagou e **não tem** o ensaio da IEC 60034-18-42. Por isso a camada propagada **não vira um terceiro tier** — vira contrato de tipo (Sprint 5), que vale igual em todos os tiers.

### 3.3 Por que `pro_engineering` para o estudo de manobra, e por que este nome

O que se vende ali é o **caso montado e executado** — pico, T1, dv/dt, TRV por fase —, da mesma classe determinística de `PREMIUM_RELAY_LIBRARY` e `NBR_17227_TEMPLATE`, os dois únicos itens hoje em `pro_engineering` (`feature_gates.py:91-92`).

**Adotei o nome `EMT_SWITCHING_STUDY` e não `EMT_SOLVER`** (duas lentes propuseram `EMT_SOLVER`). Razão: **o solver não é gateado**, e um nome que promete gatear o solver induz o erro na próxima sessão. `app/simulation/emt/circuit.py:1046` (`Solver.run`), os modelos companheiros de Dommel e a inicialização fasorial ficam abertos — é EMT genérico, publicado desde 1969, e gateá-los quebraria as suítes de EMT sem proteger nada.

### 3.4 Onde o decorador entra — e a discordância entre as lentes, resolvida

Uma das lentes queria o decorador **só** na função `run()` de um estudo novo em `app/postprocessor/studies/`; as outras duas queriam nos pontos de entrada físicos. **Adotei o híbrido**, porque cada um cobre um caminho que o outro não cobre. A lista abaixo é a lista completa — e é maior que a do handoff porque a via `SwitchingCampaign` vaza a manchete comercial inteira sem passar por `life_summary`:

| Onde | Feature | Por quê |
|---|---|---|
| `app/simulation/emt/cases/atp_reference.py:2181` — `build_reference_model` | `EMT_SWITCHING_STUDY` | é o ponto de entrada auto-declarado do caso, e é por onde os scripts entram |
| `app/simulation/emt/cases/motor_switching.py:823` — `MotorSwitchingCase.build` | `EMT_SWITCHING_STUDY` | caminho paramétrico do mesmo cenário |
| `app/postprocessor/prognosis/switching_campaign.py:398` — `life_summary` | `RUL_INSULATION` | é a função que devolve o resultado comercial |
| `app/postprocessor/prognosis/switching_campaign.py:440` — `campaign_from_summary` | `RUL_INSULATION` | é o caminho de releitura de JSON, que contorna o EMT inteiro |
| `app/postprocessor/prognosis/switching_campaign.py:269` — `SwitchingCampaign.terminal_rate` | `RUL_INSULATION` | **vazamento medido** (ver abaixo) |
| `app/postprocessor/prognosis/switching_campaign.py:285` — `SwitchingCampaign.accumulate` | `RUL_INSULATION` | via de dano que não passa por `life_summary` |
| `app/postprocessor/prognosis/switching_campaign.py:691` — `survival` | `RUL_INSULATION` | curva de sobrevivência sobre a mesma amostra |
| `app/postprocessor/prognosis/switching_campaign.py:860` — `exponent_robustness` | `RUL_INSULATION` | é o veredito de decisão, o argumento de venda |
| `app/postprocessor/studies/rul_insulation.py` — `run()` (Sprint 7) | `RUL_INSULATION` | é o ponto de entrada da GUI, e falha **cedo**, antes de custo |

**O vazamento, medido nesta sessão.** Sob `OLIVAS_BUILD_EDITION=community` (tier `educational`), montar a campanha à mão a partir de `SwitchingCampaign` e `ManeuverOutcome` — ambos reexportados pela fachada `prognosis` — e chamar `terminal_rate().describe()` devolve `8 travessias em 150 manobras: p = 5.3% (<= 8.9% a 95 %), 18.8 manobras esperadas até a primeira`, sem qualquer verificação de licença. Decorar só `life_summary` e `campaign_from_summary` deixaria essa via aberta.

Padrão obrigatório: `@requires_feature` imediatamente acima da função, como em `app/postprocessor/reliability_monte_carlo.py:242`, `arc_flash_monte_carlo.py:287`, `power_flow_monte_carlo.py:174`, `audit_trail.py:294` e `report_html.py:601`.

**Nunca nas fachadas.** Um gate em `app/simulation/emt/__init__.py` não cobriria o caminho real de uso, porque a fachada não reexporta `vcb`, `snubber`, `arrester`, `flashover`, `nonlinear` nem `vcb_scenarios` (§2.1).

### 3.5 O degrau entre as duas features é de graça

`_TIER_ORDER` (`feature_gates.py:45`) já é ordem total, com `pro_engineering` abaixo de `enterprise`, e `is_feature_available` compara ranks via `_tier_rank` (`:55`, usado em `:211`). Quem tem `enterprise` satisfaz `EMT_SWITCHING_STUDY` automaticamente. **Não escreva mecanismo de dependência entre features** — o handoff §5 sugere "o segundo dependendo do primeiro" como se fosse preciso inventar algo; não é.

### 3.6 A armadilha que faria o gate nascer decorativo

`tests/conftest.py:28-41` é um fixture **`autouse`** que força `set_tier_override("enterprise")` em **toda** a suíte. Um teste de gate que não sobrescreva explicitamente passa por engano, e um vazamento futuro não seria detectado por teste nenhum. Todo teste de gate tem de chamar `set_tier_override` no `setup_method`, como fazem os `test_pp_v4_1_0_*`.

### 3.7 Decisão que NÃO é sua, e tem de ser tomada antes do Sprint 3

O gate é de **runtime**, e o fonte é público sob Apache 2.0. `build/olivas_community.spec` **não exclui nenhum módulo de análise** — li o arquivo: `excludes` (`:55-68`) contém apenas `tkinter`/`tcl`/`tk`, `unittest`/`test` e submódulos de PySide6, e `hiddenimports` (`:36-52`) inclui `app.commercial.feature_gates`. Qualquer fork remove os decoradores em uma linha de `sed`.

Se o RUL vai ser vendido por R$ 4.500–9.000/ano/seat, **o dono do produto precisa decidir**: (a) o módulo entra em `excludes` do spec Community, (b) sai do fonte público para o bundle Pro fechado, ou (c) aceita-se o gate de runtime como suficiente. **Escale isso; não decida sozinho.** Isso muda o que se escreve no Sprint 3.

**Registre a escalação, não a deixe em parágrafo.** `docs/CONTEXT_PRESERVATION_PROTOCOL.md` §3.3 exige que toda decisão adiada vá para `docs/SKIPPED_BACKLOG.md`, com (a) referência à origem e (b) justificativa (política em `docs/SKIPPED_BACKLOG.md:8-10`). A lista está hoje em **0 itens, cap 15** (`:14`), então cabe. O registro é tarefa do **Sprint 1**, não do 11 — do contrário a decisão some ao fim da sessão, que é exatamente o modo de falha que a 8ª garantia existe para impedir.

**Nota relacionada, e que é insumo da mesma decisão:** `docs/MONETIZATION_PLAN.md:73` descreve o spec Community como "sem `app/commercial/` + sem MC + sem AI", o que contradiz o arquivo real. Corrija a linha no Sprint 2, junto com o nome do arquivo.

---

## 4. Sprints de construção

Doze sprints, numerados de 0 a 11. Cada um tem um comando que decide se ele aconteceu.

**Regra de release que atravessa todos eles:** `docs/CONTEXT_PRESERVATION_PROTOCOL.md` §3.4 diz literalmente "Se feature backend é órfã GUI → P0 imediato (não defere)", e `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` §8.3 declara "Backend órfão é proibido a partir de v3.1.0". O módulo já está órfão hoje. Portanto: **nenhuma release pode ser cortada antes do Sprint 8**, e o Sprint 10, que acrescenta backend novo, traz junto o seu próprio gatilho na GUI. Não é sequência implícita — é regra do plano.

---

### Sprint 0 — Audit de abertura e ponto de restauração

**Objetivo:** cumprir a 1ª e a 5ª garantias antes de tocar código. `docs/SESSION_HANDOFF.md:26` manda auditar (`vX.Y.Z_BACKLOG_AUDIT.md`) antes de qualquer mudança, e `:30` exige "Ponto de restauração (snapshot em `restore_points/<versao>_baseline/`)"; `docs/CONTEXT_PRESERVATION_PROTOCOL.md` §3.2 repete ("Restore point criado a CADA release antes de tocar código") e `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` §4 item 6 a cobra no fechamento.

**Novo**
* `docs/v4.2.0_BACKLOG_AUDIT.md`, no template dos audits anteriores.
* `restore_points/v4.2.0_baseline/` — snapshot de `app/` e `tests/`, no formato que `docs/SESSION_HANDOFF.md:60-67` documenta (`cp -r restore_points/<versao>/app_snapshot app/` para reverter).

**Critério de aceite**
```
test -f docs/v4.2.0_BACKLOG_AUDIT.md
test -d restore_points/v4.2.0_baseline/app_snapshot
test -d restore_points/v4.2.0_baseline/tests_snapshot
```

**Repita o snapshot antes do Sprint 2 e antes do Sprint 10** — são os dois que mexem em arquivo já ancorado por teste.

---

### Sprint 1 — Baseline verde, cobertura mensurável e a escalação registrada

**Objetivo:** deixar a suíte verde e a cobertura instalável **antes** de acrescentar uma linha do add-on. Pelo `docs/CONTEXT_PRESERVATION_PROTOCOL.md` §3.5, uma suíte vermelha já faz de qualquer release um draft — e ela **está vermelha hoje, por um defeito que nada tem a ver com o módulo**.

**Editar**
* `tests/test_pp_v2_1_0_i18n_coverage.py:39-41` — o teste `test_en_es_parity` procura `Path("D:/000 - UFMG - DOUTORADO/MVP/app/i18n/translations")`. Trocar por `Path(__file__).resolve().parents[1] / "app" / "i18n" / "translations"`.
* `requirements.txt` — acrescentar `pytest-cov` e `pytest-timeout`, hoje instalados só no CI (`.github/workflows/test.yml:48`).
* `docs/SKIPPED_BACKLOG.md` — registrar a decisão escalada da §3.7 (gate de runtime sobre fonte público *vs.* exclusão do módulo do bundle Community), com origem, justificativa e o nome de quem decide. A lista está em 0/15, então cabe.

**Critério de aceite**
```
python -m pytest -q tests/test_pp_v2_1_0_i18n_coverage.py
grep -q "pytest-cov" requirements.txt && grep -q "pytest-timeout" requirements.txt
grep -q "olivas_community.spec" docs/SKIPPED_BACKLOG.md
```
O pytest deve devolver `12 passed`. **Hoje devolve, verificado nesta sessão:**
`FileNotFoundError: [Errno 2] No such file or directory: 'D:/000 - UFMG - DOUTORADO/MVP/app/i18n/translations/en.json'` → `1 failed, 11 passed in 0.10s`.

**Risco fechado:** o teste corrigido não revela divergência EN/ES. Medido nesta sessão: `app/i18n/translations/en.json` e `es.json` têm **133 chaves cada**, e `set(en) ^ set(es)` é vazio.

---

### Sprint 2 — Tirar dado de produção de dentro de `tests/`, e fechar o empacotamento

**Objetivo:** fazer o caso de referência sobreviver a um bundle que não distribui `tests/`. É o bloqueio **duro** de empacotamento que o handoff não menciona — e vem com um segundo, da mesma classe, que nenhum sprint cobria.

**Estado verificado hoje:** `app/simulation/emt/cases/atp_reference.py:320-327` define
```python
REFERENCE_JSON_PATH: Path = (
    Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "atp"
    / "referencia_regime_permanente.json"
)
```
e `build/olivas_pro.spec:28-42` declara em `datas` **apenas** `app/preprocessor/atp_templates`, `app/preprocessor/catalog_specs` e `app/resources`. `tests/` não vai no bundle. `load_reference` (`:544`) levanta `FileNotFoundError` com a mensagem de que é a fonte única da verdade e não tem substituto sintético. **Um `.exe` gerado antes deste sprint quebra no primeiro clique do cliente, e não em nenhum teste.**

**O segundo bloqueio: `hiddenimports`.** Nenhum dos três `.spec` menciona `app.simulation` ou `app.postprocessor.prognosis` (grep vazio). A convenção do próprio repositório é registrar ali o que é descoberto por import tardio — `build/olivas_atp_studio.spec:53` traz o comentário "Hidden imports — força inclusão de módulos descobertos via lazy import", e `build/olivas_pro.spec:61-62` traz "GUI dialogs descobertos via lazy import" seguido de `app.gui.license_dialog` e `app.gui.api_key_dialog`. Os Sprints 7 e 8 tornam o módulo alcançável **apenas** por import dentro de função; sem `hiddenimports` o PyInstaller não o empacota.

**Novo**
* `app/simulation/emt/cases/data/referencia_regime_permanente.json` — **`git mv`**, não `cp`.
* `tests/test_pp_v4_2_0_rul_empacotamento.py`.

**Editar**
* `atp_reference.py:320-327` — `Path(__file__).resolve().parent / "data" / …`, seguindo o precedente de `app/preprocessor/vcb_model_emitter.py:44`.
* As três citações de procedência que apontam para o caminho antigo: `atp_reference.py:19` (docstring do módulo), `tests/test_emt_caso_referencia_atp.py:10` (docstring) e `docs/research/rul_isolamento/07_AUDITORIA_DO_CASO_ATP.md:16`. (`grep -rn 'referencia_regime_permanente'` devolve exatamente quatro ocorrências: essas três mais a própria definição em `atp_reference.py:325`.)
* `build/olivas_pro.spec`, `build/olivas_community.spec`, `build/olivas_atp_studio.spec` — bloco `datas` no formato de `atp_templates`, **e** bloco `hiddenimports` com `app.postprocessor.studies.rul_insulation`, `app.postprocessor.prognosis`, `app.simulation.emt.cases.atp_reference` e `app.gui.rul_insulation_dialog`.
* `docs/MONETIZATION_PLAN.md:72-73` — duas correções: os arquivos reais são `build/olivas_pro.spec` e `build/olivas_community.spec` (o plano nomeia `build/build_pro.spec` e `build/build_community.spec`), **e** a descrição "sem `app/commercial/` + sem MC + sem AI" é falsa contra o arquivo (`olivas_community.spec:36-52` inclui `app.commercial.feature_gates` em `hiddenimports`; `:55-68` não exclui módulo de análise nenhum).

**Os dois `.atp` ficam onde estão** — `tests/fixtures/atp/` —, mas pela razão certa: eles são insumo de **teste**, não de produção. Nenhum código de produção os lê; as menções em `app/simulation/emt/cases/atp_reference.py:19`, `vcb.py:1205`, `vcb_scenarios.py:284`, `snubber.py:663` e `:1049` são citações `[REPO:]` em docstring. O único consumo real é o do adaptador do Sprint 10, em teste. O JSON, ao contrário, é lido em runtime por `load_reference` — daí a distinção que este sprint faz.

**Anote a armadilha adjacente, que não é deste sprint mas confunde quem lê `conftest.py`:** `tests/conftest.py:12` define `REF_FILE = str(Path(__file__).parent.parent / "trt_all_motors_dt_ea.atp")` — a **raiz do repositório**, onde o arquivo não existe (`ls *.atp` na raiz não devolve nada). O fixture `ref_project` é skip-tolerant e o docstring (`:19-24`) registra "removido em 404a995 do public release", com `pytest.skip` em `:23-24`. Ou seja: os testes que pedem esse fixture são pulados em silêncio nesta árvore. Isso é insumo do Sprint 10 (ver risco lá), não deste.

**Critério de aceite**
```
python -c "from app.simulation.emt.cases.atp_reference import REFERENCE_JSON_PATH as p; \
assert 'tests' not in p.parts, p; assert p.is_file(), p; print('ok', p)"
grep -l 'cases/data\|cases\\\\data' build/*.spec | wc -l                    # 3
grep -l 'app.postprocessor.studies.rul_insulation' build/*.spec | wc -l     # 3
grep -c 'referencia_regime_permanente' docs/research/rul_isolamento/07_AUDITORIA_DO_CASO_ATP.md
python -m pytest -q tests/test_emt_caso_referencia_atp.py                   # 68 passed
```

**Risco:** duplicar em vez de mover cria duas fontes da verdade que divergem em silêncio. Use `git mv`, e refaça o snapshot do Sprint 0 antes — os 68 testes de `tests/test_emt_caso_referencia_atp.py` dependem desse arquivo (verificado nesta sessão: 68 passed em 126,38 s). Segundo risco: `build/olivas_pro.spec` tem um filtro defensivo (`FORBIDDEN_PATHS_IN_BUNDLE`) que descarta `datas` por substring de caminho — confirme que `data` e `cases` não batem nele antes de fechar.

---

### Sprint 3 — Gate comercial: duas Features, decoradores nos nove pontos

**Precondição:** a decisão da §3.7 tomada, e registrada no `SKIPPED_BACKLOG` desde o Sprint 1.

**Novo:** `tests/test_pp_v4_2_0_rul_gate.py`.

**Editar**
* `app/commercial/feature_gates.py` — duas constantes em `class Feature` após `:80`, duas entradas em `FEATURE_TIER_MAP` após `:95`.
* Os nove pontos de decoração da tabela da §3.4.
* `scripts/campanha_rul.py:163`, `scripts/varredura_vcb.py:204`, `scripts/varredura_rrds.py:103` — capturar `LicenseRequiredError` e imprimir a mensagem de upgrade em vez de traceback.
* `docs/MONETIZATION_PLAN.md` §2 e §3 — as duas linhas novas.

**A decisão de reprodutibilidade que este sprint tem de tomar explicitamente.** A regra "não chamar `set_tier_override` dentro dos scripts" (o docstring de `feature_gates.py:144-151` diz "em produção, não chamar") deixa as sete campanhas de referência irreproduzíveis, e isso precisa ser escolhido, não herdado. `current_tier` (`:156-205`) resolve por: (1) `_TIER_OVERRIDE`, (2) `OLIVAS_BUILD_EDITION=community`, que apenas **rebaixa** para `educational`, (3) JWT do license server, (4) chave HMAC legada em QSettings, (5) default `educational`. **Não existe variável de ambiente que eleve o tier** — `_BUILD_EDITION_ENV` (`:37`, lida em `:176`) é a única. Portanto "quem reproduz define o override fora do script" não tem implementação: sem licença real ou QSettings povoado, `scripts/campanha_rul.py` termina em `LicenseRequiredError` e os JSON deixam de ser regeneráveis — o que colide com o §3.1 anti-alucinação (valores publicados reproduzíveis por golden test) e com a dimensão 2 de superação do `PTW_TOTAL_PARITY_DIRECTIVE` §1.2 ("API Pythonica embutível + open-source").

Escolha **uma** e escreva a razão no PR:

* **(a)** gatear apenas o orquestrador do Sprint 7, deixando `life_summary`, `campaign_from_summary` e `terminal_rate` abertos — o gate protege o produto, não a API;
* **(b)** acrescentar em `feature_gates.py` um caminho de desenvolvimento explícito e documentado (variável de ambiente de dev, com aviso em log a cada uso), e usá-lo na reprodução;
* **(c)** declarar que reproduzir as campanhas exige licença `enterprise`, e registrar isso como limitação do laudo e no `README` dos scripts.

**Critério de aceite — duas metades, ambas obrigatórias**

(a) Dentro do pytest, com `set_tier_override` explícito no `setup_method`:
```
python -m pytest -q tests/test_pp_v4_2_0_rul_gate.py tests/test_pp_v4_1_0_commercial_sprint1.py
```
com `pro_engineering` → `build_reference_model` constrói e `life_summary` levanta `LicenseRequiredError`; com `enterprise` → ambos passam; com `educational` → ambos levantam.

(b) **Fora** do pytest, provando que os **dois** vazamentos fecharam:
```
OLIVAS_BUILD_EDITION=community python -c \
"from app.postprocessor.prognosis.switching_campaign import campaign_from_summary as c; \
 c(withstand_level_kV=21.64, peaks_pu=[1.0], crossed=[False])"

OLIVAS_BUILD_EDITION=community python -c \
"from app.postprocessor.prognosis import SwitchingCampaign, ManeuverOutcome; \
 c = SwitchingCampaign(withstand_level_kV=21.64, \
     outcomes=[ManeuverOutcome(index=0, peak_pu=1.0, crossed_envelope=False)]); \
 print(c.terminal_rate().describe())"
```
Ambos têm de terminar com `LicenseRequiredError`. **Hoje ambos terminam com sucesso** — o segundo imprime a manchete comercial inteira sob tier `educational`. Se a metade (b) não entrar no CI, o gate é decorativo e o sprint não aconteceu (ver §3.6).

(c) Regressão: `python -m pytest -q tests/test_emt_*.py tests/test_pp_prognosis_core.py tests/test_pp_switching_campaign.py` continua verde.

---

### Sprint 4 — Registro único das 87 limitações

**Objetivo:** dar às 87 chaves um caminho até o laudo. Hoje elas não têm nenhum.

**Estado verificado:** `app/postprocessor/audit_trail.py:338` define um `KNOWN_LIMITATIONS` de **7 chaves**, e `format_limitations_html` (`:408`) filtra em `:413-415` com `if k in KNOWN_LIMITATIONS`, **descartando em silêncio** o que não conhece. A interseção entre as 87 chaves do módulo e essas 7 é **vazia** (medida em runtime). Um laudo montado hoje imprimiria bloco de limitações **vazio** para a seção de RUL — o pior modo de falha possível para um módulo com responsabilidade patrimonial.

**Novo**
* `app/postprocessor/limitations_registry.py` — `collect_limitations()` unindo os 11 dicionários; `applicable_keys(config)` devolvendo **só o subconjunto pertinente à corrida**.
* `tests/test_pp_v4_2_0_limitations_registry.py`.

**Editar**
* `app/postprocessor/audit_trail.py:385` (`format_limitations_block`) e `:408` (`format_limitations_html`) — parâmetro `catalog: dict[str, str] = KNOWN_LIMITATIONS`, e registrar em log (ou levantar, em modo estrito) a chave pedida e desconhecida, em vez de descartá-la.

**Critério de aceite**
```
python -c "
from app.postprocessor.limitations_registry import collect_limitations as c
d=c(); assert len(d)>=87, len(d)
for k in ('emt_case_doc_a_rrds_prevents_clearing','rul_params_not_calibrated',
          'emt_arrester_two_point_curve','emt_flashover_withstand_is_not_breakdown',
          'rul_campaign_bernoulli_assumes_independence'):
    assert k in d, k
print('ok', len(d))"
```
A asserção é `>= 87`, e não `== 87`, porque o Sprint 10 pode acrescentar chaves ao adaptador; o teste companheiro é que trava o conjunto, varrendo os módulos **por introspecção** e falhando se aparecer um `KNOWN_LIMITATIONS` não registrado.

Âncoras dos dicionários, verificadas em runtime: `vcb.py:2227` (14), `snubber.py:973` (11), `motor_switching.py:956` (8), `atp_reference.py:2215` (7), `jmarti.py:2251` (7, `JMARTI_LIMITATIONS`), `flashover.py:479` (6), `nonlinear.py:636` (4), `arrester.py:378` (3), `switching_campaign.py:923` (3), fachadas em `emt/__init__.py:311` (19) e `prognosis/__init__.py:184` (15) — união de 87.

**Conjunto mínimo que `applicable_keys(config)` tem obrigatoriamente de devolver:**

* sempre que a saída carregar `manobras_terminais`, `taxa_de_travessia` ou `manobras_ate_travessia` → `emt_flashover_withstand_is_not_breakdown` e `rul_campaign_bernoulli_assumes_independence`;
* sempre que a saída carregar número de envelhecimento, dano ou AHI → `rul_params_not_calibrated` e `rul_synergy_lower_bound`;
* sempre que a saída carregar `energia_J` ou `n_reignicoes` → `rul_energy_surge_impedance_proxy`, `rul_measurement_point` e `rul_reignition_count_user_premise` (`prognosis/__init__.py:216`, `:223`, `:271`), porque a energia por evento é proxy via impedância de surto — a campanha usou `impedancia_de_surto_ohm = 46.99`;
* sempre que o cenário de disrupção estiver ativo → `emt_flashover_clamped_waveform_is_not_a_result`;
* sempre que houver para-raios → `emt_arrester_two_point_curve`.

**Risco:** ilegibilidade. 87 marcadores num bloco só viram boilerplate, e boilerplate tem o mesmo efeito prático de não declarar nada. Por isso `applicable_keys(config)` é obrigatório — o laudo recebe o escopo da corrida, nunca o catálogo inteiro. Não quebra o teste existente: `tests/test_pp_v0_92_audit_trail.py:309` usa `issubset`, não igualdade.

---

### Sprint 5 — Contrato de dados versionado, com a certeza no tipo

**Objetivo:** dar serialização explícita ao prognóstico **e** tornar impossível, por construção, renderizar uma grandeza da camada propagada como escalar. As duas coisas no mesmo sprint porque são o mesmo tipo.

Contexto: em 21.861 linhas de produção existem exatamente **dois** `as_dict` (`health_index.py:140` e `atp_reference.py:1886`). Não há schema.

**Novo**
* `app/postprocessor/prognosis/contracts.py` — `RUL_SCHEMA_VERSION = "rul_result.v1"`; `Certeza` (`CONTADO` / `PROPAGADO` / `DECISAO`); `Quantidade(valor, certeza, faixa, procedencia)` que **levanta `ValueError` na construção** se `certeza == PROPAGADO` e `faixa is None`; `to_dict`/`from_dict` para `StressProfile`, `StressEvent`, `ManeuverOutcome`, `TerminalRate` e os dicionários de `life_summary` e `CombinedDamageAccumulator.summary`; `campaign_from_json(path_or_dict)` reconstruindo do bloco `perfis`.
* `tests/test_pp_rul_contracts.py`.

**`campaign_from_json` NÃO é código novo — é uma mudança de casa.** A reconstrução já existe e está em produção: `scripts/campanha_rul.py:134-160`, função `_reconstroi(linha)`, que monta `StressEvent` a partir de `picos_kV` / `T1_us` / `dvdt_kV_por_us` / `energia_J` / `n_reignicoes` e devolve `ManeuverOutcome`. Ela carrega uma regra sutil, comentada em `:150-151`: **uma manobra medida sem excursão recebe perfil VAZIO, não `None`** ("a manobra foi medida e não produziu excursão acima do limiar de detecção"). **Mova `_reconstroi` para `contracts.py` e faça o script importá-la** — escrever a segunda cópia é exatamente a segunda fonte da verdade que a §6.20 proíbe. A regra do perfil vazio vira invariante testada.

**O contrato v1 tem de carregar a amostra do VCB por manobra.** `campanha_rul_n150.json` hoje não a carrega (§2.3), e sem ela o Sprint 6 não fecha. O schema v1 acrescenta, por manobra, `rrds_kV_por_ms`, `corte_A`, `didt_A_por_us`, `tempo_de_arco_us` e `separacao_s` — os mesmos campos que `varredura_vcb_n150_dt200ns.json` já grava em `realizacoes` —, mais `polo_condutor`, que é o que fixa o estrato. Campos ausentes no JSON histórico desserializam como `None`, nunca como zero.

**Editar**
* `app/postprocessor/prognosis/switching_campaign.py` — novo método `life_report()` **ao lado** de `life_summary` (`:398`), que chama `life_summary` e só embrulha. `life_summary` fica byte a byte intocado, para não mexer nos 78 testes de `tests/test_pp_switching_campaign.py`.
* `app/postprocessor/prognosis/__init__.py:130` (`__all__`) e `:184` (nova chave declarando o que o schema v1 **não** carrega — e, se `EkfRulEstimator` ficar fora do escopo v1, dizendo isso ali).
* `stress_profile.py`, `damage_models.py`, `rul_estimator.py`, `health_index.py` — declarar `__all__` (hoje nenhum tem).
* `scripts/campanha_rul.py` — gravar com `json.dumps(..., allow_nan=False)`, serializando `inf` como `null` mais um campo textual; e gravar a amostra do VCB por manobra.

**Mapa fixo de certeza:**

| Grandeza | Certeza |
|---|---|
| `taxa_de_travessia`, `manobras_ate_travessia`, `manobras_ate_travessia_cota_inferior`, `manobras_terminais` | `CONTADO` |
| `manobras_por_envelhecimento`, `dano_acumulado`, AHI (`health_index.py:273`), `CombinedDamageAccumulator.rul_years` (`damage_models.py:1071`), `EkfRulEstimator.predict_rul` (`rul_estimator.py:419`), `rul_from_damage` (`:530`) | `PROPAGADO`, faixa obrigatória |
| `caminho_dominante`, veredito de `exponent_robustness` | `DECISAO` |
| `manobras_ate_o_fim` | herda a certeza do caminho dominante |
| `PeakDistribution` (`switching_campaign.py:508`), `SurvivalCurve` (`:613`) | `CONTADO` — são estatística de população sobre a amostra medida |

**Critério de aceite**
```
python -c "
from app.postprocessor.prognosis.contracts import (
    campaign_from_json, to_dict, from_dict, RUL_SCHEMA_VERSION)
p='docs/research/rul_isolamento/anexos/dados/campanha_rul_n150.json'
c=campaign_from_json(p); a=to_dict(c); b=to_dict(from_dict(a))
assert a==b, 'round-trip quebrou'; assert a['schema']==RUL_SCHEMA_VERSION
print(a['configuracao'])"
python -m pytest -q tests/test_pp_rul_contracts.py
```
`campaign_from_json` aceita caminho **ou** dicionário já carregado; o critério exercita a forma de caminho.

O teste tem de conter, obrigatoriamente: (a) `Quantidade(valor=1.44e6, certeza=PROPAGADO, faixa=None)` levanta `ValueError`; (b) para cada chave de `life_summary` existe uma `Quantidade` de mesma magnitude em `life_report` — igualdade valor a valor sobre o JSON de referência; (c) reprodução **exata** dos cinco campos do bloco `resumo` nas duas configurações: `8780114.820168754` / `1437362.395920339`, `18.75` / `inf`, `11.199162055251845` / `50.0`, `0.05333333333333334` / `0.0`, `1.6172909228227014e-05` / `1.0435781569473676e-04`; (d) a invariante do perfil vazio de `_reconstroi`.

**Discordância resolvida:** uma lente queria derivar o schema dos contratos C1–C4 de `04_ARQUITETURA_MVP_RUL_OLIVAS.md`. **Adotei derivar dos JSON que existem** (blocos `configuracao` / `resumo` / `manobras`), mantendo apenas o *nome* `rul_result.v1` de C3 por continuidade. Razão: o documento 04 está desatualizado por medição (§2.2) e criar uma terceira forma a partir dele daria duas fontes da verdade.

**Risco:** `life_summary` e `life_report` divergirem com o tempo. Mitigação obrigatória: `life_report` **chama** `life_summary`; o teste (b) trava a equivalência. O contrato só vale se as superfícies dos Sprints 8 e 9 consumirem `life_report` e **nunca** `life_summary`.

---

### Sprint 6 — Um único estimador da taxa, rotulado

**Objetivo:** ligar à campanha o estimador pós-estratificado que **já existe** em `app/simulation/emt/vcb_scenarios.py:969` (`stratified_rate`) e impedir que ele e o 5,3 % apareçam no mesmo laudo sem rótulo (§1.1). Este sprint é *wiring* e rotulagem de estrato, não implementação de estimador.

**Precondição:** o campo `polo_condutor` + `rrds_kV_por_ms` por manobra, entregue pelo contrato do Sprint 5. Sem ele o número não é derivável do JSON: `campanha_rul_n150.json` só tem `indice`, `com_para_raios`, `pico_pu`, `reignicoes`, `atravessou_envelope` e `perfis`, e `stratified_rate` exige travessias e contagens **por estrato**.

**Se o Sprint 5 não puder regravar o JSON** (regravar exige rerodar as 300 manobras), o caminho alternativo — e ele tem de ser escrito no teste, passo a passo, não subentendido — é re-derivar as triplas de amostra deterministicamente, com a mesma chamada de `scripts/campanha_rul.py:186`: `sweep_three_pole_samples(scenario('literatura'), n=150, seed=20260903, piso_separacao_s=0.014, janela_tempo_de_arco_s=(0.0, 1e-4))`, e definir explicitamente que **o polo que fixa o estrato é o condutor por último**. Escolha um dos dois caminhos e escreva qual.

**Novo:** `tests/test_pp_v4_2_0_taxa_estratificada.py`.

**Editar**
* `app/postprocessor/prognosis/switching_campaign.py` — `life_summary` (`:398`) passa a devolver `estimador ∈ {"uniforme","pos_estratificado"}` e `taxa_de_travessia_desvio`, escolhidos por parâmetro.
* `app/simulation/emt/vcb_scenarios.py` — envolver o par `(p, sd)` já devolvido por `stratified_rate` (`:969`) num tipo consumível pela campanha; `escalation_strata` está em `:860`.

**Critério de aceite:** sobre os **mesmos** 150 desfechos, o teste reproduz `5,333 %` no modo uniforme e `4,134 % ± 1,319 %` no pós-estratificado. Os dois valores estão verificados nesta sessão contra o código e contra `docs/research/rul_isolamento/11_REDUCAO_DAS_LIMITACOES.md` l. 136 (tabela) e l. 148 (refinamento), com a partição 0/107 e 8/43 declarada em l. 130-131. Mais um teste que **falha** se o HTML trouxer os dois valores sem os dois rótulos.

**Risco:** `TerminalRate` (`switching_campaign.py:124`) é `frozen` e carrega contagens, não (p, sd); 78 testes o exercitam. **Mantenha-o intacto e acrescente um segundo tipo**, escolhido por parâmetro — não o substitua.

---

### Sprint 7 — O estudo: ponto de entrada único, gate aplicado, motor importado preguiçosamente

**Objetivo:** dar ao módulo uma camada de orquestração em `app/postprocessor/studies/` que a GUI possa consumir **sem nunca importar `app.simulation.emt` no topo**, e que **recuse o passo de integração errado**.

**Novo**
* `app/postprocessor/studies/rul_insulation.py` — `RulInsulationStudyResult` (manobras por caminho, caminho dominante, taxa com rótulo e IC, cota inferior contada, dispersão do expoente, chaves de limitação do escopo) e

```python
def run(
    project=None,
    *,
    campaign_json=None,
    case=None,
    cache=None,
    config=None,
    dt_s: float = PRODUCTION_DT_S,
) -> RulInsulationStudyResult: ...
```

decorado com `@requires_feature(Feature.RUL_INSULATION)`, na assinatura de `app/postprocessor/studies/short_circuit.py:107` mais o `dt_s` que a guarda exige. **Todo import de `app.simulation.emt.*` dentro da função.**
* `tests/test_pp_studies_rul.py`.

**Dois modos, explicitamente separados — e o script chama só um deles.**

* **Modo releitura** (`campaign_json=...`): barato, sem EMT. Compõe `campaign_from_json` + `CombinedDamageAccumulator` + `AssetHealthIndex` + `life_report`. É este o modo que a GUI abre por padrão e que o critério de aceite exercita.
* **Modo execução** (`case=...`): caro e paralelo. `case` é um `AtpReferenceCase` já construído (ou `None` para o caso de referência com `dt_s` do parâmetro); o modo executa a amostragem e o pool, e é onde `scripts/campanha_rul.py` passa a entrar.

`scripts/campanha_rul.py:163` (`main()`) passa a chamar **o modo execução**, deixando de reimplementar a cadeia — hoje ele faz amostragem (`sweep_three_pole_samples`, `:186`), pool (`ProcessPoolExecutor`, `:207`) e construção e execução do modelo por manobra (`_executa`, `:82`). O Risco 1 abaixo se aplica ao **modo releitura**: nele `run()` só compõe. No modo execução, `run()` orquestra, mas continua sem fórmula própria — a física fica nos componentes que ele chama.

**Editar**
* `app/postprocessor/studies/__init__.py` — importar o módulo e o tipo de resultado, e acrescentá-los ao `__all__` (o arquivo hoje registra `short_circuit`, `coordination`, `arc_flash_study`); documentar na docstring da hierarquia que `rul_insulation` é standalone e que o modo execução é caro.
* `app/simulation/emt/cases/atp_reference.py` — acrescentar `PRODUCTION_DT_S: float = 2.0e-7` ao lado de `DT_S` (`:338`), **sem alterar `DT_S`**, e ao `__all__` (`:2288`).

**Guarda de passo — obrigatória.** `atp_reference.py:338` define `DT_S = 1.0e-6`, que é `[FATO: arquivo]` e está ancorado nos 68 testes de `tests/test_emt_caso_referencia_atp.py`; é também o passo que o estudo declara inadequado. Medido nos dois JSON: a mediana do pico do motor é **1,751 pu a 1 µs** (`varredura_vcb_n150.json`, `literatura|sem_snubber`, `pico_motor_pu.p50`) contra **2,117 pu a 0,2 µs** (`varredura_vcb_n150_dt200ns.json`, `literatura|nenhuma`) — o valor fino é **20,9 % maior**, ou seja o passo grosso erra o corpo da distribuição. **A guarda vai no orquestrador**, porque mudar `DT_S` quebraria a ancoragem no arquivo. `run(..., dt_s=1e-6)` tem de levantar `ValueError`.

**Critério de aceite**
```
python -c "
import sys
from app.commercial.feature_gates import set_tier_override as s
s('enterprise')
from app.postprocessor.studies import rul_insulation
assert 'app.simulation.emt' not in sys.modules, 'importou o motor EMT no topo'
r = rul_insulation.run(campaign_json='docs/research/rul_isolamento/anexos/dados/campanha_rul_n150.json')
print(r.dominant_path, r.maneuvers_to_end, r.terminal_rate)"
python -m pytest -q tests/test_pp_studies_rul.py
```
mais um caso com `pro_engineering` que exige `LicenseRequiredError`, e um `pytest.raises(ValueError)` para `dt_s=1e-6`.

**Risco 1:** o estudo virar um segundo lugar onde a física mora. No modo releitura `run()` **não contém fórmula própria**; o teste compara o resultado do estudo com a chamada direta a `life_summary` e exige igualdade.

**Risco 2, verificado:** `campaign_from_summary` (`:440`) diz no próprio docstring (`:448-452`) que a taxa terminal fica disponível mas `accumulate()` **levanta**, porque sem forma de onda não há dano a integrar. No caminho de releitura por resumo agregado, o resultado tem de expor `maneuvers_by_aging=None`, **nunca zero**. Para o caminho de envelhecimento use o bloco `perfis` do JSON (`campaign_from_json`, Sprint 5), não `campaign_from_summary`.

---

### Sprint 8 — Ponto de entrada na GUI, sem religar `app.simulation` à interface

**Objetivo:** fechar a 7ª garantia (`docs/PTW_TOTAL_PARITY_DIRECTIVE.md` §8.3; `docs/SESSION_HANDOFF.md` l. 37-43) por um caminho que **não revoga** a decisão de v0.92.1.

**A tensão, e como ela se resolve.** `app/gui/main_window.py:694-699` registra, em comentário, uma decisão arquitetural explícita: *"Toda a integração ATP/EMTP foi DESVINCULADA do app principal (v0.92.1); módulos `app.simulation` e bridges permanecem disponíveis APENAS via API Python como projeto secundário, sem entry-point na UI."* Isso está em tensão direta com a 7ª garantia. **Adotei:** a GUI depende do **estudo** em `app/postprocessor/studies/`, e o estudo importa o motor EMT preguiçosamente dentro da função — que é o padrão que o próprio repositório já pratica em `app/gui/reliability_dialog.py:205-208`. Nenhuma das duas convenções é revogada.

**Novo**
* `app/gui/rul_insulation_dialog.py` — **três abas, uma por camada de certeza, nunca no mesmo painel**:
  * **"Manobra"** — pico / T1 / dv/dt / TRV por fase, via `trv_summary` (`atp_reference.py:2141`);
  * **"Campanha"** — taxa contada com o rótulo do estimador do Sprint 6, N_term, cota inferior de 11,2, e a **estatística de população** vinda de `PeakDistribution` (`switching_campaign.py:508`) e `SurvivalCurve` (`:613`), nunca o desfecho de uma manobra específica (§5.3);
  * **"Decisão"** — `exponent_robustness` (`switching_campaign.py:860`), que recomputa sobre perfis já simulados sem simular nada, e `ExponentRobustness.describe()` (`:844`).
* `app/gui/rul_worker.py` — `QThread` com sinal de progresso e cancelamento.
* `tests/test_gui_rul_dialog.py` (`QT_QPA_PLATFORM=offscreen`).

**Editar**
* `app/gui/main_window.py` — a ação entra no `analysis_menu`, imediatamente antes de `act_rep` (o "📄 Relatório completo", em `:678`), com `setStatusTip` citando a IEC 60034-15 e o tier Empresarial; handler no molde de `_on_show_reliability`.
* Cinza-fora por `is_feature_available`, e captura **explícita** de `LicenseRequiredError` no slot.

**Critério de aceite**
```
QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_gui_rul_dialog.py
python -c "
import sys, app.gui.main_window
assert 'app.simulation.emt' not in sys.modules, \
  'a GUI voltou a importar o motor EMT no topo — decisao v0.92.1 (main_window.py:694-699) violada'
print('fronteira GUI preservada')"
grep -n 'rul_insulation' app/gui/main_window.py | head -3
```
Mais: com `pro_engineering`, a aba "Manobra" habilitada e as abas 2 e 3 **desabilitadas, com o resultado de referência do JSON carregado como amostra e CTA de upgrade** — muro não vende, degrau vende. Com `enterprise`, as três habilitadas.

**Riscos**
* **UX de licença, primeiro caso do repositório.** `is_feature_available` **não aparece uma vez** em `app/gui/` — o grep é vazio. O único contato da GUI com `feature_gates` é `app/gui/license_dialog.py:169`, que importa `current_tier` dentro de `_refresh_status` (`:168`) e o usa em `:177` apenas para exibir o tier. E o único diálogo que chama função gateada captura `Exception` genérica (`reliability_dialog.py:225-227`, `except Exception as e:  # noqa: BLE001`), o que transformaria `LicenseRequiredError` numa string crua. Para este módulo isso é inaceitável.
* **Custo de execução.** Δt = 0,2 µs custa 5× por execução. **Não rode em diálogo modal.** Ordens de grandeza estimadas pelas lentes (~21 s por manobra, ~105 min para as 300 do conjunto de referência num núcleo) **não foram reverificadas por mim** — meça antes de dimensionar a barra de progresso.

---

### Sprint 9 — Seção de laudo, PDF e i18n

**Objetivo:** levar o resultado ao artefato que sai da empresa **sem que a camada propagada consiga aparecer como número**.

**Novo**
* `app/postprocessor/rul_report.py` — inclusive a função que monta o objeto de relatório a partir de um `RulInsulationStudyResult` (Sprint 7), que é o insumo do critério abaixo.
* `tests/test_pp_v4_2_0_rul_report.py`.

**Editar**
* `app/postprocessor/bus_pipeline.py:761` — `BusPipelineReport` é o dataclass que `generate_html_report` recebe (`report_html.py:601`) e **não tem campo algum de RUL**: seus campos são todos de análise de barramento (`bus_id`, `Ik_pp_kA`, `incident_energy_cal_cm2`, `relay_suggestions`, `topology_chains`, `asymmetric_fault_result`, `decay_result`…). Acrescente `rul_report: object = None` — `Optional` com default, como exige a regra de backward-compat de `docs/CONTEXT_PRESERVATION_PROTOCOL.md` §3.2. Sem isso, nada do que este sprint prescreve tem caminho de execução.
* `app/postprocessor/report_html.py` — `sections.append(_build_rul_section(report))` entre `:669` (warnings) e `:672` (`_build_limitations_block`), condicionado a `is_feature_available(Feature.RUL_INSULATION)` **e** a `report.rul_report is not None`; a seção consome **`life_report`, nunca `life_summary`**.
* `app/postprocessor/report_html.py:731` — `_build_limitations_block` passa a receber as chaves de escopo do Sprint 4.
* `app/postprocessor/report_pdf.py` — seção equivalente, antes do bloco de limitações.

**Critério de aceite** — quatro asserções obrigatórias sobre o HTML gerado a partir do JSON de referência, pela cadeia `rul_insulation.run(campaign_json=…)` → `rul_report.build(...)` → `BusPipelineReport(rul_report=…)` → `generate_html_report`:

1. a string do valor de `manobras_por_envelhecimento` **nunca** aparece sem a faixa e sem a saída de `ExponentRobustness.describe()` no mesmo elemento;
2. o bloco de limitações contém, no mínimo, `rul_params_not_calibrated`, `rul_synergy_lower_bound`, `emt_flashover_withstand_is_not_breakdown`, `rul_campaign_bernoulli_assumes_independence` e as demais chaves de `flashover` pertinentes ao escopo;
3. onde aparece `18,75` aparece também a cota inferior `11,2`, no mesmo elemento;
4. com `set_tier_override('pro_engineering')` o HTML sai **sem** a seção de RUL e sem vazar nenhum número da campanha.

Mais: `python -c "import json; d=json.load(open('.../campanha_rul_n150.json')); json.dumps(d['resumo'], allow_nan=False)"` deixa de levantar (hoje levanta `ValueError: Out of range float values are not JSON compliant`).

**i18n — discordância resolvida, e declarada como exceção.** O item 3 do checklist do handoff §6 manda envolver strings em `_()` desde o dia zero, e `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` §5.3 põe "i18n desde dia-0: novas strings UI sempre passam por `_()` para PT/EN/ES" entre as práticas encorajadas (a dimensão 5 de superação, §1.2, é justamente i18n). Verifiquei: `app/i18n/__init__.py:107` define `_()`, e **`app/gui/main_window.py` não a usa uma única vez** — os 5 casamentos de `grep "_("` são `__init__(` e `raise_()`; o único contato com i18n é `from app.i18n import set_locale` em `:179`, em 4.348 linhas. Adotar `_()` **só** no módulo novo criaria um terceiro estilo.

**Adotei, como exceção declarada à §5.3 da diretriz:** registrar as strings novas do **laudo** em `en.json` e `es.json` (o laudo é o artefato que sai da empresa, e o `_()` de `app/i18n/__init__.py:107` é passthrough em PT — sem registro, a tradução simplesmente não existe), e manter o **menu** em PT-BR literal, como o resto de `main_window.py`. Registre em `docs/SKIPPED_BACKLOG.md` como *exceção consciente à §5.3*, com a razão (evitar terceiro estilo), o nome de quem decide e **a versão em que a política de i18n da GUI será resolvida** — porque `docs/SKIPPED_BACKLOG.md:5-6` exige que a lista esteja zerada antes de qualquer release final, e um item sem prazo bloqueia esse zeramento.

---

### Sprint 10 — Adaptador `AtpProject → caso executável`: fechar a lacuna do `.atp`

**Objetivo:** fazer o módulo resolver **o caso do cliente**, e não um caso equivalente montado à mão. Refaça o snapshot do Sprint 0 antes de começar.

**Aqui o handoff está errado em premissa, e é a correção mais cara deste documento.** A §10 dele manda "começar pelo leitor de `.atp`". **O leitor já existe:** `app/core/parser.py:53`, `parse_file(filepath) -> AtpProject`. Executei-o nesta sessão sobre `tests/fixtures/atp/trt_all_motors_dt_ea.atp` e ele devolve **31 ramos, 9 chaves, 3 fontes, 3 MODELS (`VCB_Rr`, `VCB_Rs`, `VCB_Rt`)**, com `header.frequency = 60.0`, `header.delta_t = 1e-06`, `header.t_max = 0.045` — exatamente `FREQUENCY_HZ` (`:335`), `DT_S` (`:338`) e `T_END_S` (`:341`) de `atp_reference.py`.

Mais decisivo: o bloco `DATA` do `USE VCB_RR` devolve, **dígito a dígito**, `T_OPENr:=0.01455`, `RRDS_Ar:=0.801`, `RRDS_Br:=1.226`, `I_CHOPr:=1.`, `DIDT_CRITr:=5.`, `RARCr:=20.`, `ROPENr:=1.E6`, `COPENr:=6.` — os mesmos valores constantados à mão em `atp_reference.py:407` (`VCB_SEPARATION_TIME_S = (0.01455, 0.02475, 0.02481)`), `:419` (`VCB_RRDS_A_KV_PER_MS = 0.801`) e `:428` (`VCB_ARC_RESISTANCE_OHM = 20.0`).

**A lacuna não é um leitor: é um adaptador de algumas centenas de linhas, com defeitos reais e delimitados.**

**Escopo, delimitado por fonte.** `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` §5.2 lista "não cita o manual porque não tenho aqui" como padrão inaceitável, e o §6 risco 3 diz "bloqueia sprint correspondente até manual ser obtido — não codar sem fonte". Portanto o adaptador cobre **apenas** o que é decodificável com fonte: os 14 `DataParam` do bloco `DATA` de cada `USE`, a fonte, o motor e o cabo. **Ficam fora de escopo, e vão para `docs/SKIPPED_BACKLOG.md` como bloqueio por fonte ausente** (não só para `KNOWN_LIMITATIONS`), os três itens da §4 de `06_CASO_BASE_ATP_ESPECIFICACAO.md` (l. 76-80): a matriz acoplada 6×6 do transformador sob `USE AR`, que precisa da seção 5.3 do manual de referência do ATP; o ramo fonte–triângulo com termos `-1.`, com a mesma dependência; e a convenção dos campos R'/A'/B' do cartão de linha sob comprimento negativo.

**Novo**
* `app/simulation/emt/cases/from_atp_project.py` — `case_from_atp(atp: AtpProject) -> AtpReferenceCase` e `vcb_parameters_from_use(use: UseInstance) -> AtpVcbParameters`.
* `tests/test_emt_from_atp_project.py`.
* **Gatilho na GUI, no mesmo sprint:** item "Abrir caso `.atp`…" no diálogo do Sprint 8, com handler que chama `case_from_atp` por import tardio, mais o smoke test manual escrito no PR. Backend novo sem gatilho é órfão, e órfão é proibido desde v3.1.0 (`PTW_TOTAL_PARITY_DIRECTIVE.md` §8.3).

**Editar**
* `app/simulation/emt/cases/__init__.py:61` — exportar as duas funções.
* `app/simulation/emt/cases/atp_reference.py:1413`/`:1577` — `AtpReferenceCase` / `.build` aceitam os parâmetros injetados. **Enumere os campos novos aqui, porque hoje eles não existem:** o dataclass tem exatamente 19 campos (`with_snubber`, `dt_s`, `t_end_s`, `use_card_neutral`, `didt_convention`, `reignition_factor`, `gap_capacitance_F`, `max_reignitions`, `separation_times_s`, `snubber_breakover_V`, `snubber_resistance_ohm`, `snubber_holding_current_A`, `cable_phasor_reading`, `atp_model_compatibility`, `zero_crossing_order`, `reference_path`, `vcb_samples`, `motor_arrester_system_voltage_V`, `motor_flashover_level_V`), e **não** tem `source_peak_V`, `motor_inductance_H` nem `cable_modal_surge_ohm`. Acrescente-os como `Optional[...] = None`, conforme a regra de backward-compat de `docs/CONTEXT_PRESERVATION_PROTOCOL.md` §3.2, com `None` significando "usar a constante do módulo":

  | Campo novo | Tipo | Default |
  |---|---|---|
  | `source_peak_V` | `float \| None` | `None` |
  | `motor_inductance_H` | `float \| None` | `None` |
  | `motor_resistance_ohm` | `float \| None` | `None` |
  | `cable_modal_surge_ohm` | `tuple[float, float, float] \| None` | `None` |
  | `cable_modal_velocity` | `tuple[float, float, float] \| None` | `None` |
  | `cable_modal_resistance_ohm` | `tuple[float, float, float] \| None` | `None` |
  | `vcb_parameters` | `tuple[AtpVcbParameters, ...] \| None` | `None` |

* `app/simulation/emt/vcb.py:1528-1544` — corrigir o docstring de `for_pole`, que hoje afirma `[FATO: arquivo, linhas 526-604]` que "os polos diferem em `T_OPEN`, `I_CHOP` e `DIDT_CRIT`; todo o resto é comum". **É falso contra o arquivo** (ver defeito 4 abaixo).
* `app/simulation/emt/cases/atp_reference.py:2215` — registrar em `KNOWN_LIMITATIONS` **apenas o que for novo do adaptador**. As duas limitações que o handoff mandaria acrescentar **já existem ali**: `emt_atp_ref_transformer_not_decoded` ("A matriz acoplada 6×6 do transformador sob a opção `USE AR` NÃO foi decodificada…") e `emt_atp_ref_real_modal_matrix` ("O cabo a jusante usa a PARTE REAL da matriz de transformação modal punçada no arquivo…"). Reutilize-as; duplicá-las quebraria o registro do Sprint 4.
* `docs/research/rul_isolamento/05_MOTOR_EMT_DEDICADO.md` §11.3 — a lacuna declarada muda de estado.

**Os defeitos, todos verificados em execução — não são hipóteses**

1. **O decodificador genérico fatia errado o cartão de parâmetros distribuídos.** Para
   `-1X0001A01ATA               0.04901436 46.99493446 93424.65873         -1. 1  30`
   o parser devolve, literalmente: `resistance='0.04'`, `inductance='901436'`, `capacitance='46.99'`, enquanto os campos verdadeiros são `R = 0.04901436`, `Z = 46.99493446`, `v = 93424.65873` — registrados em `atp_reference.py:358-378` (`CABLE_MODAL_SURGE_OHM`, `CABLE_MODAL_VELOCITY`, `CABLE_MODAL_RESISTANCE_OHM`, todos **tuplas de três modos**: `CABLE_MODAL_SURGE_OHM == (46.99493446, 99.49766584, 986.1619784)`). O adaptador precisa de fatiamento próprio por coluna e **não pode consumir** `b.resistance` / `b.inductance` / `b.capacitance` dos ramos com `semantic_type == 'line'`. Note ainda que esses campos vêm como **`str`**, não `float`.

2. **Unidades de R e L do motor: mH.** O ramo do motor vem `R=.691, L=8.9795` e vira `MOTOR_INDUCTANCE_H = 8.9795e-3` (`atp_reference.py:352`). Conversão errada **não levanta exceção nenhuma** — a simulação roda e o número sai errado.

3. **Unidades de L e C do bloco `USE`: não há convenção única, e o adaptador NÃO pode aplicar regra única.** O módulo declara isso em `app/simulation/emt/vcb.py:2227`, chave `emt_vcb_atp_lc_unit_convention`:

   > "MODO LITERAL. Os campos de indutância e capacitância do arquivo (LARC = 5.E-5, LOPEN = 6.E-7, CARC = 2.E-5, COPEN = 6.) NÃO admitem uma única convenção de unidade consistente: com o cartão de dados diversos sem XOPT/COPT, a leitura padrão do ATP é mH e µF, que dá COPEN = 6 µF (compatível com a especificação do caso) mas CARC = 20 pF (a especificação registra 20 nF). Os valores adotados como padrão deste módulo são os da especificação — 50 µH, 0,6 µH, 20 nF e 6 µF…"

   As constantes estão em `vcb.py:1257-1265`: `ATP_L_CLOSED_H = 2.0e-3`, `ATP_L_ARC_H = 50.0e-6`, `ATP_L_OPEN_H = 0.6e-6`, `ATP_C_ARC_F = 20.0e-9`, `ATP_C_OPEN_F = 6.0e-6`. Um mapeamento homônimo mH/µF produziria `c_arc_F = 2e-11` contra `2e-8` — **erro de 1000×** no elemento que o próprio módulo diz mudar a frequência natural da malha de reignição por ordens de grandeza no estado de ARCO. Ou o adaptador adota os valores de especificação já parametrizados em `AtpVcbParameters` (`vcb.py:1476-1484`) e registra a divergência, ou expõe a convenção como parâmetro explícito. Não há terceira opção, e o critério de aceite passa a cobrir os quatro campos.

4. **Os polos não são idênticos fora de T_OPEN/I_CHOP/DIDT_CRIT.** Lido nos blocos `USE` do arquivo: o polo **S** traz `RCLOSEDs:= 0.002` e `LCLOSEDs:= 1.`, contra `RCLOSED:=0.001` e `LCLOSED:=0.002` nos polos R e T — **500× de diferença na indutância série do polo fechado**. `for_pole` (`vcb.py:1528-1544`) só sobrepõe `t_open_s`, `i_chop_A` e `didt_crit_A_per_us`, e usa os escalares `ATP_R_CLOSED_OHM = 0.001` (`:1251`) e `ATP_L_CLOSED_H = 2.0e-3` (`:1257`). Um adaptador construído sobre a premissa "`AtpVcbParameters` já é campo a campo esse bloco" reproduz silenciosamente o polo S errado. Acrescente `ATP_R_CLOSED_OHM` e `ATP_L_CLOSED_H` como **tuplas por polo** e corrija o docstring.

5. **Não case os polos por `semantic_type`.** Verificado: os três polos do disjuntor voltam classificados como **`tacs_controlled`**, e não `vcb` (`XX0006→X0001C`, `XX0014→X0001B`, `XX0022→X0001A`, cartões tipo 13). O adaptador tem de casar pelos MODELS `VCB_R*` e pelos blocos `USE`. Atenção à API: `UseInstance` expõe `model_name`, `instance_name`, `inputs`, `outputs` e `data` (lista de `DataParam` com `name`/`assigned_value`) — **não tem `.name` nem `.parameters`**.

6. **O modo de compatibilidade tem de ser fixado, e é ele que decide se o caso do cliente produz resultado.** `atp_reference.py:2215`, chave `emt_atp_ref_literal_model_defect`, declara que no modo LITERAL "o teste compara a corrente com ela mesma. Consequência verificada: T_ZERO permanece em -1, V_WITH permanece nulo, NENHUMA reignição é declarada"; e recomenda `zero_crossing_order=ATP_ZERO_ORDER_DEFERRED` para "a leitura em que o teste compara amostras consecutivas — que é [INFERÊNCIA FÍSICA] sobre a intenção do autor do MODEL, não o que o arquivo executa". Os dois campos existem em `AtpReferenceCase` com defaults `atp_model_compatibility = False` (`:1467`) e `zero_crossing_order = ATP_ZERO_ORDER_LITERAL` (`:1468`). **`case_from_atp` tem de fixar os dois explicitamente e dizer por quê**, e o critério de aceite tem de verificar que o modo escolhido produz reignição — caso contrário um adaptador "fiel ao arquivo do cliente" devolve zero travessias e o resultado comercial inteiro desaparece sem erro nenhum.

**Critério de aceite — contra os valores literais do cartão, não contra a constante do módulo**

A comparação `assert c.source_peak_V == R.SOURCE_PEAK_V` é tautológica se o adaptador copiar a constante em vez de decodificar o cartão. O critério compara com os **literais do arquivo**, e usa as constantes só como referência cruzada:

```
python -c "
from app.core.parser import parse_file
from app.simulation.emt.cases.from_atp_project import case_from_atp, vcb_parameters_from_use
import app.simulation.emt.cases.atp_reference as R
import app.simulation.emt.vcb as V

p = parse_file('tests/fixtures/atp/trt_all_motors_dt_ea.atp')
ps = [vcb_parameters_from_use(u) for u in p.uses]

# literais do bloco DATA de cada USE, transcritos do arquivo
assert tuple(x.t_open_s for x in ps) == (0.01455, 0.02475, 0.02481) == R.VCB_SEPARATION_TIME_S
assert tuple(x.i_chop_A for x in ps) == (1.0, 2.0, 2.0) == R.VCB_CHOPPING_CURRENT_A
assert tuple(x.didt_crit_A_per_us for x in ps) == (5.0, 15.0, 15.0) == R.VCB_DIDT_CAPABILITY_A_PER_US
assert ps[0].rrds_a_kV_per_ms == 0.801 == R.VCB_RRDS_A_KV_PER_MS
assert ps[0].r_arc_ohm == 20.0 == R.VCB_ARC_RESISTANCE_OHM
assert tuple(x.r_open_ohm for x in ps) == (1.0e6, 1.0e6, 1.0e6)

# polos NAO sao identicos: S difere em RCLOSED e LCLOSED
assert tuple(x.r_closed_ohm for x in ps) == (0.001, 0.002, 0.001)
assert tuple(x.l_closed_H  for x in ps) == (2.0e-3, 1.0e-3, 2.0e-3)

# convencao de L/C: valores da especificacao, nao mH/uF ingenuo
assert ps[0].c_arc_F  == V.ATP_C_ARC_F  == 20.0e-9
assert ps[0].c_open_F == V.ATP_C_OPEN_F == 6.0e-6
assert ps[0].l_arc_H  == V.ATP_L_ARC_H  == 50.0e-6
assert ps[0].l_open_H == V.ATP_L_OPEN_H == 0.6e-6

c = case_from_atp(p)
assert c.source_peak_V == 11718.4337 == R.SOURCE_PEAK_V
assert abs(c.motor_inductance_H - 8.9795e-3) < 1e-12 == (abs(c.motor_inductance_H - R.MOTOR_INDUCTANCE_H) < 1e-12)
assert c.cable_modal_surge_ohm == (46.99493446, 99.49766584, 986.1619784) == R.CABLE_MODAL_SURGE_OHM
assert (p.header.frequency, p.header.delta_t, p.header.t_max) == (60.0, 1e-06, 0.045)
assert (p.header.frequency, p.header.delta_t, p.header.t_max) == (R.FREQUENCY_HZ, R.DT_S, R.T_END_S)

# o modo de compatibilidade fixado produz reignicao
m = c.build(); r = m.run()
assert r.reignitions > 0, 'modo de compatibilidade nao produz escalada'
print('adaptador reproduz os cartoes digito a digito')"
python -m pytest -q tests/test_emt_from_atp_project.py tests/test_emt_caso_referencia_atp.py
```

A linha `l_closed_H` acima assume a leitura `LCLOSEDs := 1.` como 1 mH; se o sprint escolher outra convenção, o literal muda e a **razão** vai no PR. O que não pode é o polo S sair igual aos outros dois.

Qualquer erro de coluna, de unidade ou de polo reprova.

**Risco de fixture.** `tests/test_emt_from_atp_project.py` depende de `tests/fixtures/atp/trt_all_motors_dt_ea.atp`, e a política declarada do repositório retira `.atp` das releases públicas — `tests/conftest.py:19-24` registra "removido em 404a995 do public release" para o arquivo homônimo da raiz e faz `pytest.skip`. Decida e escreva no PR: ou o fixture de `tests/fixtures/atp/` é declaradamente público, ou o teste novo também nasce skip-tolerant.

---

### Sprint 11 — Travas de arquitetura, documentação datada e fechamento de release

**Objetivo:** transformar em teste executável cada fronteira que este plano estabeleceu, e datar os documentos cujas contagens não batem mais com a árvore.

**Novo**
* `tests/test_arch_rul_boundaries.py` — quatro asserções, por **`ast.parse`** e inspeção apenas dos `Import`/`ImportFrom` **em nível de módulo**, ignorando (a) os aninhados em `FunctionDef` e (b) os aninhados em blocos `if TYPE_CHECKING:` — é exatamente essa distinção que o plano protege, e regex sobre linhas vira ruído:
  1. `prognosis` não importa `emt` em nenhum arquivo;
  2. `emt` só toca `prognosis` dentro de função (`app/simulation/emt/probes.py:275`) ou sob `TYPE_CHECKING` (`probes.py:47-50`) — sem a exceção (b) a trava nasce vermelha;
  3. nenhum arquivo de `app/` fora do módulo importa `app.simulation.emt` no topo;
  4. a agregação de limitações do laudo alcança as 87 chaves.
* `docs/v4.x_GUI_AUDIT_RUL.md`, no template de `docs/v3.1.0_GUI_AUDIT.md`. **Crie-o já ao fim do Sprint 8 e reabra-o ao fim do Sprint 10** — o critério 10 da §8.3 do `PTW_TOTAL_PARITY_DIRECTIVE` exige "deep GUI audit APÓS CADA sprint backend"; aqui ele só é consolidado.

**Editar — documentação canônica de release (sem ela a release é draft)**
* `docs/SESSION_HANDOFF.md` §3.2 e §5 — estado do módulo e próximos passos (`PTW_TOTAL_PARITY_DIRECTIVE.md` §4 item 7 e §8.4 critério 12).
* `docs/PTW_SURPASSING_MATRIX.md` — linhas novas com **pelo menos uma dimensão de superação declarada** (`§4` item 3). A matriz é relevante em substância: `:241-246` traz a Part 8 ISIM (feature 109, "Run > Industrial Simulation", alvo v4.0.0, status ⏳) e `:211-222` a Part 6 TMS, ambas com 0 entregues — o motor EMT próprio é o candidato natural a fechá-las. Se a decisão for que o RUL está fora das 124 features PTW, **escreva a justificativa na matriz**; não a deixe sem entrada.
* `docs/CONTEXT_PRESERVATION_PROTOCOL.md` §4 — atualizar o snapshot.
* `CHANGELOG.md` — entrada `[4.2.0]` (a mais recente hoje é `[4.0.0-beta] — 2026-05-01`, `:7`) e `app/core/version.py:1959-1960` (`VERSION_TUPLE`, `PRE_RELEASE`).
* `docs/SKIPPED_BACKLOG.md` — confirmar que os dois itens abertos por este plano (§3.7, registrado no Sprint 1; i18n da GUI, registrado no Sprint 9) têm origem, justificativa e versão-alvo, e que a lista continua dentro do cap de 15.

**Editar — documentação que envelheceu.** Acrescente um cabeçalho de supersessão no formato do documento 10, que é o único que o pratica: uma linha de citação começando por `> **Superado.**` ou `> **Números superados.**` (l. 56 e l. 73), seguida do que foi superado e por qual medição. O documento 08 **não** tem esse formato — o que ele traz são ressalvas de escopo (`> **Valor convergido.**`, l. 83; `> **Ressalva acrescentada depois.**`, l. 136) —, então não o tome como precedente.

* `docs/research/rul_isolamento/00_INDICE.md` §3.8 — todas as contagens de código estão vencidas (§2.2 deste documento traz o par medido); é a página que o integrador é mandado abrir primeiro.
* `docs/research/rul_isolamento/04_ARQUITETURA_MVP_RUL_OLIVAS.md` — cabeçalho de superado; as contagens erradas estão em `04:3`, `04:13`, `04:163` e `04:458`.
* `docs/research/rul_isolamento/05_MOTOR_EMT_DEDICADO.md` §12.1 — cita `vcb.KNOWN_LIMITATIONS (:1003)` com 8 chaves e `snubber (:621)` com 6; hoje são `vcb.py:2227` com 14 e `snubber.py:973` com 11.
* `docs/HANDOFF_MODULO_RUL_ISOLAMENTO.md` — §2 (l. 35, tempo de suíte não reproduzido), §4.1 (77,5→3,45 e 128→6 são comparações entre passos; 4,1 % e 18,75 são estimadores diferentes), §5 (l. 103, 72 → 87 limitações), §7.1 (l. 144, 4,3× → 6,11× por manobra), §9 (l. 166, "Onze documentos" → 12), §10 (o leitor de `.atp` já existe em `app/core/parser.py:53`).
* `scripts/README.md` — não documenta `campanha_rul.py`, `varredura_vcb.py` nem `varredura_rrds.py` (`grep` devolve vazio), e os três são o modo como as campanhas de referência foram produzidas. Documente também o caminho de reprodução escolhido no Sprint 3.

**Critério de aceite**
```
python -m pytest -q tests/test_arch_rul_boundaries.py
python -m pytest -q --cov-fail-under=80 \
  --cov=app/simulation/emt --cov=app/postprocessor/prognosis \
  --cov=app/postprocessor/studies \
  --cov=app/postprocessor/limitations_registry.py \
  --cov=app/postprocessor/rul_report.py \
  --cov=app/gui/rul_insulation_dialog.py --cov=app/gui/rul_worker.py \
  --cov-report=term tests/ -k "emt or prognosis or campaign or rul"
```
`--cov-fail-under=80` é obrigatório: sem ele o comando imprime a cobertura e sai com código 0 qualquer que seja o número, e o critério vira comentário. Os quatro `--cov` extras cobrem os módulos criados por este plano que os três originais deixavam de fora — e é sobre módulos **novos** que `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` §4 item 4 e `docs/CONTEXT_PRESERVATION_PROTOCOL.md` §3.5 exigem os 80 %.

Mais o smoke test manual escrito no PR, no formato que a 7ª garantia exige: *"para usar o RUL, o usuário clica em **Análise → 🔬 Vida da isolação sob manobra de VCB…**"*, e o do Sprint 10: *"para carregar o caso do cliente, o usuário clica em **Abrir caso `.atp`…** dentro desse diálogo"*.

---

## 5. Riscos de produto que o integrador tem de gerenciar

1. **O laudo é o artefato de maior consequência.** Ele sai da empresa e vira responsabilidade contratual. Uma seção que imprima "1,44·10⁶ manobras" como escalar é o modo de falha mais caro do módulo — e é exatamente o erro que o handoff §4.2 adverte e que o próprio handoff §4.1 comete. O Sprint 5 existe para que isso seja impossível **por tipo**, não por lembrança.
2. **Travessia do envelope não é falha de isolação.** `emt_flashover_withstand_is_not_breakdown` (`flashover.py:479`): o limiar é nível de **suportabilidade de ensaio** da IEC 60034-15, a ruptura real ocorre acima dele por margem não publicada, e o ramo **não prevê o instante físico da disrupção**. A contagem é contada; a interpretação não. Vocabulário obrigatório na §1.0.
3. **Do cenário de disrupção não se cita pico.** `emt_flashover_clamped_waveform_is_not_a_result` (mesma linha): a forma de onda é grampeada, com ultrapassagem de 1,04 a 1,87 vez o limiar, e "o pico grampeado NÃO é resultado quantitativo". Cite `fracao_com_disrupcao` e `disrupcoes_max`.
4. **Dano acumulado não é métrica comparativa entre configurações.** Medido sobre `campanha_rul_n150.json`: o para-raios **multiplica o dano por 6,11× por manobra de envelhecimento** (142 manobras sem mitigação contra 150 com para-raios), porque converte falha em envelhecimento — a máquina sobrevive à manobra, e sobreviver custa dano. Lido isolado, o número recomenda **não** instalar o para-raios. Comparação só sobre `min(N_env, N_term)`, que é o que `life_summary` já entrega.
5. **A cauda de escalada não é convergida por realização.** A fração de população é estável entre 1 µs e 0,2 µs (`fracao_acima_do_teto_de_campo = 0.05333333333333334` nos dois arquivos — conferido), mas o *conjunto* de realizações muda. Exiba estatística de população — `PeakDistribution` (`switching_campaign.py:508`) e `SurvivalCurve` (`:613`) são as fontes; **nunca** o desfecho de uma manobra específica.
6. **Δt = 1 µs não serve, e é o default do código.** `atp_reference.py:338` define `DT_S = 1.0e-6` — é `[FATO: arquivo]` e está certo como tal, mas é o passo que o estudo declara inadequado: mediana de 1,751 pu contra 2,117 pu a 0,2 µs, 20,9 % de diferença. Sem a guarda do Sprint 7, qualquer tela que instancie o caso com defaults produz o número errado **em silêncio**.
7. **A curva do para-raios é reconstrução de dois pontos publicados**, escalada por regra de seleção (`arrester.py:174`, `:224`; chave `emt_arrester_two_point_curve`). Afirma margem de proteção **relativa**, não nível residual de equipamento específico. Se o cliente informar o catálogo dele, use-o.
8. **A extrapolação de 1/p supõe Bernoulli independente.** `rul_campaign_bernoulli_assumes_independence` (`switching_campaign.py:923`): a travessia é tratada como Bernoulli com p constante, o que exige (i) manobras futuras estatisticamente iguais às da campanha — deixa de valer quando o disjuntor envelhece — e (ii) ausência de correlação entre manobras consecutivas, que uma sequência de partidas abortadas viola. É a premissa que sustenta 18,75, a regra de três e a cota de "> 50 manobras", **e o caso comercial do módulo é justamente o motor manobrado sob partidas abortadas** (Documento A). A campanha de referência foi gerada com `janela_tempo_de_arco_s: [0.0, 0.0001]` e `piso_separacao_s: 0.014` fixos (`varredura_vcb_n150_dt200ns.json`, bloco `configuracao`). Chave obrigatória no laudo.
9. **O gate é de runtime e o fonte é público.** Ver §3.7 — decisão do dono do produto, antes do Sprint 3, registrada no `SKIPPED_BACKLOG` no Sprint 1.
10. **A suíte não prova que o gate funciona.** `tests/conftest.py:28-41` força `enterprise` por `autouse` em todos os testes. Ver §3.6.
11. **Gatear a campanha torna as campanhas de referência irreproduzíveis** se não houver caminho de desenvolvimento. Não existe variável de ambiente que eleve o tier (`feature_gates.py:156-205`). Escolha (a), (b) ou (c) no Sprint 3 e escreva a razão.
12. **Custo de UX.** Δt = 0,2 µs custa 5× por execução. Antes de reduzir `n` às cegas, **estratifique**: `escalation_strata` (`vcb_scenarios.py:860`) e `stratified_rate` (`:969`) já estão implementados, e o documento 11 reporta ganho de variância de 6,8× (~22 execuções igualando a precisão das 150 uniformes) — número de documento (`11_…md` l. 138-139), não reverificado por mim.

---

## 6. O que NÃO fazer

1. **NÃO escrever um leitor de `.atp` do zero.** Ele existe: `app/core/parser.py:53`. Seguir a §10 do handoff ao pé da letra é reimplementar código já testado. O trabalho real é o adaptador do Sprint 10.
2. **NÃO consumir `b.resistance` / `b.inductance` / `b.capacitance` dos ramos `semantic_type == 'line'`.** Medido: o parser devolve `'0.04'`, `'901436'`, `'46.99'` para um cartão cujos campos são `0.04901436`, `46.99493446`, `93424.65873`. O erro é silencioso: a simulação roda e o número sai errado.
3. **NÃO aplicar uma convenção única de unidade aos campos L e C do bloco `USE`.** `emt_vcb_atp_lc_unit_convention` (`vcb.py:2227`): a leitura mH/µF dá `COPEN = 6 µF` (certo) mas `CARC = 20 pF` contra os 20 nF da especificação — erro de 1000× no elemento que governa a malha de reignição. Adote os valores parametrizados em `AtpVcbParameters` ou exponha a convenção como parâmetro.
4. **NÃO supor que os três polos diferem só em `T_OPEN`, `I_CHOP` e `DIDT_CRIT`.** O docstring de `for_pole` (`vcb.py:1531-1533`) afirma isso como `[FATO: arquivo]` e está errado: o polo S traz `RCLOSEDs:=0.002` e `LCLOSEDs:=1.` contra 0.001 e 0.002 nos polos R e T.
5. **NÃO casar os polos do disjuntor por `semantic_type`.** Verificado: os três voltam como `tacs_controlled`. Case pelos MODELS `VCB_R*`.
6. **NÃO deixar `atp_model_compatibility` e `zero_crossing_order` implícitos no adaptador.** No modo LITERAL o arquivo do cliente não escala: `T_ZERO` fica em −1, nenhuma reignição é declarada, e o resultado comercial desaparece sem erro (`emt_atp_ref_literal_model_defect`, `atp_reference.py:2215`).
7. **NÃO importar `app.simulation.emt` no topo de qualquer arquivo de `app/gui/`.** Isso religa à interface o subsistema que `app/gui/main_window.py:694-699` registra como deliberadamente desvinculado em v0.92.1. Import preguiçoso dentro do handler, no padrão de `app/gui/reliability_dialog.py:205-208`.
8. **NÃO pôr `@requires_feature` nas fachadas** (`app/simulation/emt/__init__.py`, `app/postprocessor/prognosis/__init__.py`) **nem em `Solver.run`** (`circuit.py:1046`). A fachada de `emt` não reexporta `vcb`, `snubber`, `arrester`, `flashover`, `nonlinear` nem `vcb_scenarios` — um gate ali não cobre o caminho real. Um gate no solver quebra as suítes de EMT e mata o degrau de upgrade.
9. **NÃO gatear apenas `life_summary` e `campaign_from_summary`.** Medido: sob tier `educational`, `SwitchingCampaign.terminal_rate().describe()` (`switching_campaign.py:269`) imprime a manchete comercial inteira. Os nove pontos da §3.4 são a lista completa.
10. **NÃO tratar `app/simulation/emt/__init__.py` como a superfície pública do motor.** Um laudo montado a partir das duas fachadas agrega **34 das 87** chaves; 53 chaves de auditoria não chegariam ao relatório.
11. **NÃO confiar em `format_limitations_html`** (`audit_trail.py:408`) para levar as limitações ao laudo. A linha `:415` filtra `if k in KNOWN_LIMITATIONS` e descarta em silêncio; a interseção entre as 87 chaves e as 7 daquele registro é **vazia**.
12. **NÃO deixar `REFERENCE_JSON_PATH`** (`atp_reference.py:320`) **apontando para `tests/fixtures/`.** Nenhum `.spec` distribui `tests/`. Qualquer release feito antes do Sprint 2 quebra no cliente, e não nos testes.
13. **NÃO editar só `datas` nos `.spec`.** Sem `hiddenimports`, os módulos alcançados por import tardio (Sprints 7 e 8) não entram no bundle. Nenhum dos três specs menciona hoje `app.simulation` ou `app.postprocessor.prognosis`.
14. **NÃO exibir "N anos de vida remanescente" como escalar** em tela, laudo, tooltip ou log — inclusive o que vem de `CombinedDamageAccumulator.rul_years` (`damage_models.py:1071`) e de `EkfRulEstimator.predict_rul` (`rul_estimator.py:419`).
15. **NÃO usar dano acumulado como métrica comparativa** entre configurações (§5.4).
16. **NÃO repetir "77,5 → 3,45 pu" nem "128 → 6 reignições".** No mesmo Δt = 0,2 µs os pares são 76,90 → 3,45 pu e 191 → 7 reignições. E **não cite 13,13 pu como pico** — é forma de onda grampeada (§1.0).
17. **NÃO citar "uma manobra em 24" e "18,75 manobras" na mesma lista** sem dizer que são estimadores diferentes (§1.1), nem citar 18,75 sem a cota inferior de 11,2.
18. **NÃO produzir número novo a partir de `varredura_vcb_n150.json`** nem de `campanha_rul_n60.json`. Só `varredura_vcb_n150_dt200ns.json` e `campanha_rul_n150.json` são citáveis.
19. **NÃO prometer dano acumulado a partir de `campaign_from_summary`** (`switching_campaign.py:440`). O docstring `:448-452` avisa: sem forma de onda, `accumulate()` levanta. Esse caminho entrega taxa terminal e N_term; N_env exige as formas de onda ou o bloco `perfis` do JSON.
20. **NÃO inventar mecanismo de dependência entre as duas Features.** `_TIER_ORDER` (`feature_gates.py:45`) e `_tier_rank` (`:55`) já fazem o degrau.
21. **NÃO criar uma terceira Feature para a camada de envelhecimento.** Ela não é tier, é pré-condição de dado (ensaio IEC 60034-18-42 ou histórico de frota). Resolve-se no contrato de tipo do Sprint 5.
22. **NÃO derivar o schema do documento 04 (C1–C4).** Está desatualizado por medição; o contrato v1 formaliza os blocos `configuracao` / `resumo` / `manobras` que os sete JSON já contêm (§4, Sprint 5).
23. **NÃO tomar `04_ARQUITETURA_MVP_RUL_OLIVAS.md` nem `00_INDICE.md` §3.8 como fonte de contagens de código** — declaram 3.052 e 3.240 linhas de `prognosis` contra 4.235 medidas.
24. **NÃO reescrever `campaign_from_json` do zero.** A reconstrução existe em `scripts/campanha_rul.py:134-160` (`_reconstroi`), com a regra do perfil vazio em `:150-151`. Mova-a; não a duplique.
25. **NÃO duplicar em `atp_reference.KNOWN_LIMITATIONS` as chaves do transformador e da matriz modal.** `emt_atp_ref_transformer_not_decoded` e `emt_atp_ref_real_modal_matrix` já existem em `:2215`.
26. **NÃO criar `app/analysis/dielectric_stress.py`** (item E9 de `anexos/cruzamento/cruzamento_A_snubber_vcb.md`). Duplicaria `stress_profile.py:415` (`extract_stress_events`) num terceiro pacote e criaria segunda fonte da verdade para o vetor de estresse.
27. **NÃO chamar `set_tier_override` dentro dos scripts de reprodução** sem antes resolver o item 11 da §5 — e escrever a escolha no PR. `feature_gates.py:148` diz "em produção, não chamar", e não há variável de ambiente que eleve o tier.
28. **NÃO rodar a campanha em diálogo modal**, nem reduzir `n` às cegas — estratifique (§5.12).
29. **NÃO adotar `_()` só no menu do módulo novo.** `app/gui/main_window.py` não usa `_()` em lugar nenhum; um terceiro estilo é pior que a exceção declarada. Ver Sprint 9 — e registre-a como exceção à §5.3 da diretriz, com versão-alvo, não como débito sem prazo.
30. **NÃO cortar release antes do Sprint 8**, e não deixar o adaptador do Sprint 10 sem gatilho na GUI. Backend órfão é proibido desde v3.1.0 (`PTW_TOTAL_PARITY_DIRECTIVE.md` §8.3; `CONTEXT_PRESERVATION_PROTOCOL.md` §3.4, "não defere").
31. **NÃO tocar código antes do ponto de restauração** do Sprint 0, nem fazer o `git mv` do Sprint 2 e as edições do Sprint 10 sem repeti-lo.

---

## 7. Primeiro passo recomendado

**Não é o leitor de `.atp`** — ele já existe (§6.1), e o adaptador que falta é o Sprint 10.

**Não é o gate** — porque um gate posto sobre uma suíte vermelha e um `REFERENCE_JSON_PATH` que aponta para `tests/` produz um release que é draft por protocolo e quebra no primeiro `.exe`.

**O primeiro passo é o Sprint 0, e ele não escreve uma linha de produção:** `docs/v4.2.0_BACKLOG_AUDIT.md` e `restore_points/v4.2.0_baseline/`. São a 1ª e a 5ª garantias (`docs/SESSION_HANDOFF.md:26` e `:30`), e o Sprint 2 faz `git mv` de um arquivo do qual dependem 68 testes.

**O segundo passo custa uma linha.** Abra `tests/test_pp_v2_1_0_i18n_coverage.py:39-41`, troque `Path("D:/000 - UFMG - DOUTORADO/MVP/app/i18n/translations")` por `Path(__file__).resolve().parents[1] / "app" / "i18n" / "translations"`, e rode:

```
python -m pytest -q tests/test_pp_v2_1_0_i18n_coverage.py
```

Hoje isso devolve `1 failed, 11 passed in 0.10s` com `FileNotFoundError` num caminho absoluto de Windows que não existe em clone nenhum deste ambiente. Não há divergência EN/ES escondida atrás dele: 133 chaves em cada arquivo, diferença simétrica vazia, medido nesta sessão. Depois disso a árvore está em condição de receber trabalho, e o Sprint 2 (tirar o dado de produção de dentro de `tests/`, e fechar `datas` e `hiddenimports` nos três `.spec`) é o que destrava o empacotamento.

**No mesmo Sprint 1, e antes do Sprint 3:** escale ao dono do produto a decisão da §3.7 — gate de runtime sobre fonte público, ou exclusão do módulo do bundle Community — e **registre-a em `docs/SKIPPED_BACKLOG.md`** (0 itens de 15 hoje). Ela muda o que se escreve no sprint do gate, e não é decisão de integrador.

---

## 8. O que eu não verifiquei

Registro explícito, para que ninguém tome estas afirmações como conferidas:

* **A contagem de 829 testes e o tempo de execução da suíte.** Não rodei a suíte completa nesta sessão. O handoff declara 196 s; uma das lentes mediu 376,6 s. **Nenhum dos dois foi reproduzido por mim.** Coletei apenas `tests/test_emt_caso_referencia_atp.py` (68 testes, `68 passed in 126,38 s`) e `tests/test_pp_switching_campaign.py` (78 testes coletados).
* **A cobertura de testes** dos pacotes. Não a medi, logo o critério de ≥ 80 % do `CONTEXT_PRESERVATION_PROTOCOL` §3.5 (l. 72-75, cujo texto conferi) não foi exercido nesta sessão.
* **A mediana de 0,489 ms** do instante da travessia após a separação dos contatos: conferi apenas que o número está em `09_PARA_RAIOS_E_CRITERIO_DE_ACEITACAO.md` l. 292; não o recomputei.
* **O fator 2,92·10³** de dispersão do expoente: está em `11_REDUCAO_DAS_LIMITACOES.md` l. 68 (l. 76 e l. 158 arredondam para 2,9·10³), e não foi recomputado com `exponent_robustness`.
* **O ganho de variância de 6,8×** e as "~22 execuções" da estratificação: números de `11_REDUCAO_DAS_LIMITACOES.md` l. 138-139, não reexecutados. (O par 4,134 % / 1,319 %, ao contrário, **foi** reproduzido em runtime — ver §1.1.)
* **Os custos de import e de execução** citados pelas lentes (19,0 ms / 18,3 ms / 31,7 ms de import; 1,86 s para 20 ms de simulação; ~21 s por manobra a 0,2 µs; ~105 min para 300 manobras). **Nenhum foi medido por mim.** Meça antes de dimensionar a UX do Sprint 8.
* **O conteúdo de `build/olivas_atp_studio.spec`** além do bloco de `hiddenimports` (`:53-54`) e da confirmação de que o arquivo existe. De `build/olivas_pro.spec` li `datas` (`:20-42`) e `hiddenimports` (`:45-62`); de `build/olivas_community.spec` li `hiddenimports` (`:36-52`) e `excludes` (`:55-68`).
* **As afirmações normativas contra o texto da IEC 60034-15 em si.** Conferi apenas a coerência interna: `envelope_V = 21640.0` no JSON contra os 21,64 kV de $U_P$ registrados em `01_ETAPA1…md` l. 313 e l. 319.
* **Os itens indeterminados de `06_CASO_BASE_ATP_ESPECIFICACAO.md` §4** (l. 76-82) dependem da seção 5.3 do manual de referência do ATP, que não tenho. Permanecem fora do escopo do adaptador (Sprint 10) e vão para o `SKIPPED_BACKLOG` como bloqueio por fonte ausente, não só para `KNOWN_LIMITATIONS`.