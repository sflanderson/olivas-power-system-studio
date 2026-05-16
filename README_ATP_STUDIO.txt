README
OLIVAS ATP STUDIO
v0.16.0

============================================================
1. VISAO GERAL
============================================================

Olivas ATP Studio e uma aplicacao desktop em Python para leitura,
interpretacao, edicao, validacao, serializacao e execucao de
arquivos ATP/EMTP de simulacao de transitorios eletromagneticos.

O projeto foi concebido para independencia total do ATPDraw,
oferecendo uma plataforma robusta, extensivel e com integracao
a inteligencia artificial (Claude API).

============================================================
2. ARQUITETURA
============================================================

- Arquivo .atp como fonte unica da verdade
- ATP/EMTP como motor de calculo
- Python 3.11+ como plataforma principal
- PySide6 como interface grafica
- anthropic SDK para integracao com Claude API
- Modelo semantico interno para manipulacao estruturada

Ver ARCHITECTURE_ATP_STUDIO.txt para detalhes por camada.

============================================================
3. ESTRUTURA DO PROJETO
============================================================

olivas-atp-studio/
  app/
    main.py                     -- entry point
    core/
      project_model.py          -- modelo semantico (dataclasses)
      parser.py                 -- parser de arquivo .atp
      serializer.py             -- serializacao .atp
      diff_util.py              -- diff textual
    gui/
      main_window.py            -- janela principal PySide6
      chat_widget.py            -- chat com agente LLM
      compare_widget.py         -- comparacao side-by-side
      topology_widget.py        -- visualizacao topologica
    simulation/
      runner.py                 -- execucao ATP externa
      results_reader.py         -- leitor de .pl4 e .lis
    validation/
      validator_models.py       -- validacao MODEL/USE
      validator_physics.py      -- validacao fisica
      validator_vcb.py          -- validacao VCB (IEC 62271-100)
    analysis/
      transient_metrics.py      -- metricas de transitorio e TRV
      csv_export.py             -- exportacao CSV
      report_export.py          -- relatorio HTML com logo
      case_compare.py           -- comparacao entre casos
    llm/
      agent.py                  -- agente LLM (18 tools)
      project_api.py            -- API programatica do projeto
      intents.py                -- intents estruturadas
      parametric.py             -- estudos parametricos
    resources/
      logo.png                  -- logo Olivas ATP Studio
  requirements.txt
  CHANGELOG_ATP_STUDIO.txt
  TASKS_ATP_STUDIO.txt
  README_ATP_STUDIO.txt
  ARCHITECTURE_ATP_STUDIO.txt

============================================================
4. REQUISITOS
============================================================

- Python 3.11 ou superior
- PySide6 >= 6.6.0
- anthropic >= 0.90.0 (opcional, para chat com Claude)
- Pillow (opcional, para otimizacao do logo no relatorio)

============================================================
5. INSTALACAO
============================================================

1. Criar ambiente virtual:
   python -m venv .venv

2. Ativar:
   Windows:  .venv\Scripts\activate
   Linux:    source .venv/bin/activate

3. Instalar dependencias:
   pip install -r requirements.txt

4. (Opcional) Para chat com Claude:
   set ANTHROPIC_API_KEY=sk-ant-...

============================================================
6. EXECUCAO
============================================================

python -m app.main

============================================================
7. FUNCIONALIDADES
============================================================

CORE:
- Parser completo de arquivos .atp (header, MODELS, USE, BRANCH,
  SWITCH, SOURCE, OUTPUT)
- Classificacao semantica automatica de componentes
  (resistor, inductor, capacitor, snubber, VCB, transformer, etc.)
- Extracao de nos do circuito com rastreabilidade
- Serializacao com preservacao de formatacao original
- Diff textual entre original e editado

GUI (8 abas):
- Detalhes: propriedades do item selecionado na arvore
- Texto bruto: conteudo raw do arquivo .atp
- Topologia: visualizacao grafica do circuito (tema-aware)
- Validacao: mensagens com niveis (ERRO, AVISO, INFO) e cores
- Diff: diferencas entre original e versao editada
- Resultados: metricas de transitorio por variavel (.pl4)
- Agente: chat com comandos locais ou conversa livre (Claude API)
- Comparar: side-by-side entre dois casos abertos

TEMA:
- Modo escuro (padrão) e modo claro
- Toggle de tema em Menu Visualizar
- Persistencia de preferencia via QSettings
- Compatibilidade com: matplotlib, topologia, comparacao, chat

EDICAO:
- Tabela editavel de DATA do USE (com defaults do MODEL)
- Tabela editavel de INPUT do USE
- Tabela editavel de OUTPUT do USE
- Editor de MODEL DATA defaults
- Preview com diff antes de salvar

VALIDACAO:
- Consistencia MODEL/USE (referencias, contagem I/O, case mismatch)
- Duplicatas de nomes
- Sintaxe de secoes (ENDMODELS, ENDMODEL, ENDUSE, BLANK cards)
- Fisica basica (R/L/C negativos, self-loops, fontes inativas)
- Dominio VCB (faixas de parametros IEC, cobertura de fases)

SIMULACAO:
- Execucao ATP externa com timeout configuravel
- Diretorio de execucao por caso (runs/<caso>_<timestamp>)
- Log de execucao persistente
- Caminho ATP persistido via QSettings

ANALISE:
- Metricas de transitorio (pico, RMS, frequencia, amortecimento)
- TRV e RRRV com comparacao IEC 62271-100
- Leitor .pl4 robusto (Fortran unformatted + layout direto)
- Exportacao CSV (formas de onda e metricas)
- Relatorio HTML com logo Olivas embutido

AGENTE LLM:
- 18 tools no formato Claude API tool_use
- Chat com comandos locais (20+ comandos PT/EN)
- Conversa livre via Claude API (quando ANTHROPIC_API_KEY configurada)
- Loop agentic com ate 10 turnos de tool calls
- Estudos parametricos automatizados

MULTI-CASO:
- Multiplos arquivos .atp abertos simultaneamente
- Seletor de caso ativo no topo da janela
- Comparacao side-by-side de parametros entre casos

============================================================
8. COMANDOS DO CHAT
============================================================

  resumo / summary          resumo do projeto
  modelos / models          listar MODELs
  uses                      listar USEs
  modelo <nome>             detalhes de um MODEL
  use <nome>                detalhes de um USE
  header                    parametros de simulacao
  componentes [secao] [tipo]  listar componentes
  nos / nodes               listar nos
  validar / validate        executar validacoes
  executar / run            rodar simulacao ATP
  set <model> <param> <val> alterar parametro
  sweep <m> <p> <ini> <fim> estudo parametrico
  exportar <path> [mode]    exportar CSV
  relatorio <path>          relatorio HTML
  abrir <caminho>           abrir arquivo .atp
  salvar <caminho>          salvar arquivo .atp
  ajuda / help              lista de comandos

Com ANTHROPIC_API_KEY: texto livre em linguagem natural.

============================================================
9. FLUXO BASICO DE USO
============================================================

1. Abrir arquivo .atp (Ctrl+O)
2. Inspecionar estrutura na arvore (MODELs, USEs, componentes)
3. Validar o caso (Ctrl+Shift+V)
4. Editar parametros DATA do USE
5. Verificar diff (Ctrl+D)
6. Salvar como novo arquivo (Ctrl+Shift+S)
7. Executar ATP
8. Analisar resultados e metricas
9. Exportar relatorio HTML

============================================================
10. CONTEXTO DE ENGENHARIA
============================================================

Olivas ATP Studio foi desenvolvido para aplicacoes em
engenharia eletrica, especialmente estudos com:

- ATP/EMTP (transitorios eletromagneticos)
- Disjuntores a vacuo (VCB)
- Reignicao e current chopping
- Transient Recovery Voltage (TRV)
- Rate of Rise of Recovery Voltage (RRRV)
- Snubber ativo
- Modelagem MODELS/TACS
- Conformidade IEC 62271-100

============================================================
11. HISTORICO DE VERSOES
============================================================

v0.1.0  Base inicial documentada
v0.2.0  Nucleo funcional (parser, GUI, validacao)
v0.3.0  Serializacao e execucao basica
v0.4.0  Codigo funcional completo (editor, preview, diff)
v0.5.0  Parsing avancado e extracao de nos
v0.6.0  Topologia, VCB e resultados
v0.7.0  Persistencia, diff e execucao melhorada
v0.8.0  Parser semantico, analise TRV, editor MODEL
v0.9.0  Validacao fisica, agente LLM, estudos parametricos
v0.10.0 Metricas na GUI, PL4 robusto, agente Claude
v0.11.0 Chat, exportacao CSV e multi-caso
v0.12.0 Renomeacao Olivas, comparacao, Claude API
v0.12.1 Relatorio HTML com logo
v0.13.0 Documentacao arquitetural abrangente
v0.14.0 Visualizacao interativa de formas de onda
v0.15.0 Testes automatizados com 81 cobertura completa
v0.16.0 Modo escuro/claro com tema centralizador

============================================================
12. SCREENSHOTS
============================================================

A interface possui 8 abas:

[1] Detalhes   — propriedades do MODEL/USE/componente selecionado
[2] Texto bruto — conteudo raw do arquivo .atp
[3] Topologia  — grafo do circuito com nos e arestas coloridos
[4] Validacao  — lista de mensagens com cores por severidade
[5] Diff       — diferencas entre original e editado
[6] Resultados — metricas de transitorio das variaveis .pl4
[7] Agente     — chat com comandos ou conversa livre Claude
[8] Comparar   — tabela de diferencas entre dois casos

A arvore lateral mostra: Header, MODELS, USES, BRANCH, SWITCH,
SOURCE, NODES. Cada componente tem tipo semantico no label.

O seletor de caso no topo permite alternar entre arquivos abertos.

============================================================

FIM DO README
