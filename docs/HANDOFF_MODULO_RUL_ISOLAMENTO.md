# Handoff — Módulo RUL de Isolação de Estator (add-on Empresarial)

**Para:** agente responsável pela construção do Olivas PSS.
**De:** linha de trabalho `claude/isolamento-degradacao-monitoramento-dr900x`.
**Objeto:** integrar um módulo já implementado e testado, hoje **órfão**, como add-on da
licença Empresarial.

Este documento é o que você precisa ler antes de tocar em qualquer arquivo. Ele diz **o que o
módulo é**, **o que os dados contêm**, **o que já está pronto**, **o que falta** e **por que o
caminho de integração recomendado é o de add-on Empresarial e não o de feature Pro**.

---

## 1. Resumo em um parágrafo

O módulo responde a uma pergunta que o Olivas hoje não responde: *quantas manobras do disjuntor
a vácuo a isolação do estator deste motor ainda suporta?* Ele o faz por dois caminhos separados
e não somáveis — envelhecimento por acúmulo de estresse e ruptura por travessia do envelope
normativo —, entregando o mínimo dos dois. O gerador de estresse é um **motor de transitórios
eletromagnéticos próprio**, escrito em Python, que não depende de binário de terceiro. O
resultado principal é calibrado por contagem, não por curva de vida: **uma manobra em 24
atravessa o envelope da IEC 60034-15 na instalação sem mitigação; com para-raios, nenhuma em
150**.

## 2. Onde o código está

| Pacote | Linhas | Papel |
|---|---|---|
| `app/simulation/emt/` | 16 784 | Motor EMT dedicado: kernel de Dommel, MNA, CDA, linhas Bergeron e JMarti, VCB dinâmico, *snubber* a tiristor, não linearidades por compensação, para-raios ZnO, disrupção de isolação |
| `app/postprocessor/prognosis/` | 4 235 | Perfil de estresse, modelos de dano, RUL por EKF, Asset Health Index, campanha de manobras |
| `scripts/varredura_vcb.py` | — | Varredura Monte Carlo dos parâmetros do disjuntor |
| `scripts/varredura_rrds.py` | — | Varredura em grade da taxa de recuperação dielétrica |
| `scripts/campanha_rul.py` | — | Cadeia completa manobra → estresse → dano → vida |

**Suíte:** **829 testes** nas doze suítes do módulo, todos passando em 196 s [CÁLCULO PRÓPRIO: medido nesta sessão].
**Limitações declaradas:** 72, em `KNOWN_LIMITATIONS` por módulo, agregadas nas fachadas.

## 3. O que os dados contêm

Sete conjuntos em `docs/research/rul_isolamento/anexos/dados/`, todos JSON, ~2,9 MB.

| Arquivo | Conteúdo | Para que serve na integração |
|---|---|---|
| `varredura_vcb_n150.json` | 900 realizações a Δt = 1 µs: 3 cenários × 150 × (com/sem amortecedor). Por realização: instante de separação, tempo de arco por fase, corte, di/dt, RRDS, reignições, pico no motor em kV e pu, TRV e dv/dt | Conjunto histórico. **Não usar para número novo** — o passo de 1 µs erra o corpo da distribuição em 21 % |
| `varredura_vcb_n150_dt200ns.json` | 450 realizações a Δt = 0,2 µs: cenário da literatura × 150 × (sem mitigação / para-raios / registro de disrupção). Mesmos campos, mais energia no para-raios e instante da primeira disrupção | **Conjunto de referência.** É dele que sai a taxa citável |
| `varredura_rrds_constante.json` | Grade de RRDS de 5 a 50 kV/ms, 25 realizações por ponto, com e sem para-raios, capacidade de extinção constante | Critério de aceitação de Wong (forma da dependência) |
| `varredura_rrds_wong.json` | Mesma grade com a lei de extinção dependente do tempo | idem |
| `varredura_rrds_wong_estendida.json` | Grade estendida a 200 kV/ms | Localiza o máximo interior da dependência |
| `campanha_rul_n150.json` | **300 manobras com formas de onda processadas**: por manobra e por fase, cada excursão com pico, T₁, dv/dt, energia e contagem de reignições, nas duas configurações | **Conjunto de referência da cadeia completa** |
| `campanha_rul_n60.json` | Idem, 120 manobras | Histórico; seus números de envelhecimento foram superados |

Todos trazem um bloco `configuracao` com semente, passo, tensão de base, envelope adotado e
limiar de detecção — o suficiente para reproduzir qualquer linha.

## 4. O que o módulo entrega, e com que grau de certeza

Separe estas três camadas ao expor na GUI. Elas têm **status epistemológico diferente** e
misturá-las no mesmo painel seria o principal risco do produto.

### 4.1 Calibrado — pode ir a laudo como número

* **Taxa de travessia do envelope normativo.** Sai de contagem, não depende de nenhum parâmetro
  de curva de vida. Sem mitigação: $p = 4{,}1\,\% \pm 1{,}3\,\%$, ou **uma manobra em 24**. Com
  para-raios: zero em 150, logo $p \le 2\,\%$ pela regra de três — **mais de 50 manobras**, e
  não "nunca".
* **Fim de vida pelos dois caminhos.** Sem mitigação, 18,75 manobras (a travessia domina); com
  para-raios, $1{,}44\cdot10^6$ (o envelhecimento domina) — fator de 76 000. A decisão é robusta
  ao expoente não calibrado; o segundo número, não.
* **Instante da travessia.** Mediana de 0,489 ms após a separação dos contatos. Consequência
  comercial direta: **não há janela de atuação nessa escala**, o que sustenta a recomendação de
  mitigação preventiva contra proteção reativa.
* **Efeito da mitigação.** Pico máximo cai de 77,5 para 3,45 pu com para-raios; reignições, de
  128 para 6. Ambos dentro da faixa publicada.

### 4.2 Arquitetura com incerteza propagada — exibir sempre com a faixa

* **Manobras por envelhecimento.** Ordem de $10^6$ a $10^7$, mas os parâmetros da curva de vida
  **não estão calibrados** para mica-epóxi pré-formada de MT. Varrendo o expoente na faixa da
  literatura (3,8 a 11,7), a vida varia por fator de **2,9·10³**. Nunca exiba esse número sem a
  faixa.
* **Asset Health Index.** Herda a mesma incerteza.

### 4.3 Livre de calibração — o argumento de venda

A **decisão** de mitigar não depende dos parâmetros não calibrados. Varrendo o expoente na faixa
inteira, o para-raios vence em todos os pontos, e por uma razão estrutural: quando o caminho
terminal domina, a vida é $1/p$ e o expoente **não entra na conta** (dispersão exatamente 1).
É isso que o painel deve dizer ao decisor: *a recomendação é robusta; o prazo não é*.

## 5. Por que Empresarial, e não Pro

O gate técnico atual põe os Monte Carlos em `Pro+` e reserva à Empresarial multi-seat,
white-label e importador ETAP/SKM [REPO: `docs/MONETIZATION_PLAN.md`, §3]. Este módulo pertence
à Empresarial por três razões, em ordem de peso:

1. **O entregável é decisão de capital, não cálculo de projeto.** A saída é "instale para-raios
   ou troque o motor em N manobras", com custo de indisponibilidade associado. É a mesma classe
   de decisão que justifica o white-label e o SLA, e não a classe do estudo pontual.
2. **Exige dado de ativo, não só de rede.** Para sair da faixa e virar previsão, o módulo precisa
   de ensaio do sistema isolante (IEC 60034-18-42) ou de histórico de falhas da frota. Quem tem
   isso é cliente de contrato, e o ciclo de venda é de venda direta.
3. **A responsabilidade técnica é maior.** Um RUL errado tem consequência patrimonial. O tier
   Empresarial já carrega SLA, o que dá o enquadramento contratual correto para as 72 limitações
   declaradas.

**Recomendação de gate:** feature nova `Feature.RUL_INSULATION = "rul_insulation"`, mapeada a
`"enterprise"` em `FEATURE_TIER_MAP`. Siga o padrão de
`app/postprocessor/reliability_monte_carlo.py:242` — decorador `@requires_feature` na função de
entrada, não em módulo inteiro.

**Sub-gate sugerido:** o motor EMT sozinho (sem prognóstico) tem valor em `pro_engineering` como
solucionador de transitórios de manobra. Considere `Feature.EMT_SOLVER` em `pro_engineering` e
`Feature.RUL_INSULATION` em `enterprise`, com o segundo dependendo do primeiro. Isso cria degrau
de upgrade em vez de muro.

## 6. O que falta — e é bloqueante pelas convenções do repositório

O módulo viola hoje a **7ª garantia**: *"Toda feature backend implementada DEVE ter ponto de
entrada GUI … Backend órfão é proibido a partir de v3.1.0"*
[REPO: `docs/SESSION_HANDOFF.md`, l. 37-43; texto formal em
`docs/PTW_TOTAL_PARITY_DIRECTIVE.md` §8.3]. Nenhum módulo fora de `app/simulation/emt/` e
`app/postprocessor/prognosis/` os importa. Checklist mínimo para o release:

| # | Item | Referência da convenção |
|---|---|---|
| 1 | `Feature` + entrada em `FEATURE_TIER_MAP` | `app/commercial/feature_gates.py` |
| 2 | Ação de menu em `app/gui/main_window.py`, com trigger documentado | 7ª garantia, §3.4 |
| 3 | Strings via `_()` desde o dia zero | `PTW_TOTAL_PARITY_DIRECTIVE`, l. 171 |
| 4 | Seção de laudo em `app/postprocessor/report_html.py` | — |
| 5 | Entrada em `CHANGELOG.md` e `app/core/version.py` | — |
| 6 | Cobertura ≥ 80 % nos módulos novos | `CONTEXT_PRESERVATION_PROTOCOL` §3.5 |
| 7 | Smoke test manual: *"para usar o RUL, o usuário clica em…"* | §3.4 |
| 8 | Deep GUI audit no template de `docs/v3.1.0_GUI_AUDIT.md` | 7ª garantia |

Há ainda uma lacuna funcional declarada, **não bloqueante para o gate mas bloqueante para a
promessa de produto**: o motor **não lê `.atp`**. O caso é construído em Python e pode divergir
do registro, que a arquitetura declara ser a fonte única da verdade
[REPO: `docs/research/rul_isolamento/05_MOTOR_EMT_DEDICADO.md`, §11.3]. Enquanto isso não
existir, o módulo resolve *um caso equivalente*, não *o caso do cliente*.

## 7. Riscos que você tem de gerenciar no produto

1. **Não exiba dano acumulado como métrica comparativa entre configurações.** Está medido: o
   para-raios **aumenta** o dano acumulado em 4,3 vezes, porque converte falha em
   envelhecimento — a máquina sobrevive à manobra, e sobreviver custa dano. Lido isoladamente, o
   número recomendaria não instalar o para-raios. Comparação só sobre $\min(N_{env}, N_{term})$.
2. **A cauda de escalada não é convergida por realização.** A fração de população é estável entre
   Δt = 1 µs e 0,2 µs (8 de 150 nos dois), mas o *conjunto* de realizações muda. Exiba
   estatística de população; nunca o desfecho de uma manobra específica.
3. **Δt = 1 µs não serve.** Erra o corpo da distribuição em 21 %. O passo adequado é 0,2 µs, a
   2,7 % de 0,05 µs. Isso tem custo: 5× por execução. Dimensione a UX para isso — barra de
   progresso e execução em segundo plano, não diálogo modal.
4. **A curva do para-raios é reconstrução de dois pontos publicados**, escalada por regra de
   seleção. Afirma margem de proteção relativa, não nível residual de equipamento específico.
   Se o cliente informar o catálogo do para-raios dele, use-o.

## 8. Onde ganhar desempenho, se precisar

A estratificação já está implementada (`app/simulation/emt/vcb_scenarios.py`:
`escalation_strata`, `stratified_rate`). Medido: **~22 execuções bastam para igualar a precisão
das 150 uniformes** — ganho de variância de 6,8× com o mesmo orçamento sob alocação de Neyman.
Para uma UX interativa, é esse o caminho: não reduza `n` às cegas, estratifique.

## 9. Documentação técnica de apoio

Onze documentos em `docs/research/rul_isolamento/`, 5 629 linhas, com sistema de rótulos de
evidência ([FATO], [LITERATURA], [NORMA], [CÁLCULO PRÓPRIO], [HIPÓTESE], [INFERÊNCIA]). Comece
por `00_INDICE.md`. Para a integração, os relevantes são:

* `04_ARQUITETURA_MVP_RUL_OLIVAS.md` — fluxo de dados em camadas e inventário de arquivos.
* `05_MOTOR_EMT_DEDICADO.md` §11 — ponte com o prognóstico, lacuna do `.atp`, estado de órfão.
* `08` a `10` — a linha de validação: varredura, para-raios e critério de aceitação, dois
  caminhos de fim de vida.

## 10. Primeiro passo que eu recomendo

Não comece pela GUI. Comece pelo **leitor de `.atp`** (§6, lacuna funcional). Sem ele o módulo
entrega um número sobre um caso que o cliente não reconhece como o dele, e nenhuma quantidade de
polimento de interface conserta isso. Com ele, o discurso de venda fecha: *"aponte o seu arquivo
de estudo; eu digo quantas manobras a isolação aguenta e o que muda se você instalar
para-raios"*.

Depois dele, a ordem do checklist da §6.
