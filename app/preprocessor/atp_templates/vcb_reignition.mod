-- ================================================================
-- vcb_reignition.mod
-- Modelo estatístico de reignição para disjuntor a vácuo (VCB)
-- ================================================================
--
-- Referências:
-- * CIGRE WG A3.26, "Tools for the simulation of the effects of the
--   internal arc in HV gas-insulated switchgear", Technical Brochure
--   570, 2014.
-- * EPRI, "Methodology for High-Frequency Transient Studies", 1989.
-- * Helmer, J.; Lindmayer, M., "Mathematical modeling of the high
--   frequency behavior of vacuum interrupters", XVIIth ISDEIV, 1996.
--
-- Algoritmo (por pólo):
-- 1. Enquanto T < T_open: chave FECHADA, passa corrente.
-- 2. Após T_open:
--    (a) Ao cruzamento de zero da corrente, amostrar I_chop ~ N(I_chop_mean, σ²).
--        Se |i| < I_chop: abrir o arco (corte de corrente).
--    (b) Se |di/dt| > di/dt_crit(t) no instante do corte: reignição imediata.
--        di/dt_crit(t) = di/dt_0 + didt_sigma * (t - t_open)  -- endurecimento da câmara.
--    (c) Após corte, a tensão através da câmara cresce (TRV).
--        U_dielec(t) = U0_dielec + k_dielec * (t - t_corte)   -- recuperação dielétrica.
--        Se |V_chamber(t)| > U_dielec(t): reignição (breakdown).
--    (d) T_bounce: tempo de rebote mecânico após estabilização.
--
-- Saídas:
--   switch_cmd  — 1.0 para fechar a chave TACS-controlada, 0.0 para abrir.
--   reign_count — contador de reignições (para pós-processamento).
--
-- Entrada (wire via TACS):
--   i_branch    — corrente instantânea do ramo do disjuntor (A).
--   v_branch    — tensão através da chave (V).
--
-- Limitação (v0.22.1):
--   Este MODEL é EMITIDO pelo bridge, mas o wiring TACS (MEASURING no
--   ramo do disjuntor, e cartão TACS SOURCE controlando o TYPE-13) é
--   MANUAL na v0.22.1. A automação do wiring fica para v0.22.2.
--
-- ================================================================

MODEL vcb_reignition
COMMENT
  Chave a vácuo com reignição estatística (CIGRE WG A3.26).
  Requer wiring TACS manual até v0.22.2.
ENDCOMMENT

DATA
  I_chop_mean  {dflt: 5.0}          -- A, corrente média de chopping
  I_chop_sigma {dflt: 1.0}          -- A, desvio-padrão do chopping
  didt_crit_0  {dflt: 16.0}         -- A/µs, di/dt crítico inicial
  didt_sigma   {dflt: 0.034}        -- A/µs², crescimento do di/dt_crit
  k_dielec     {dflt: 17.0}         -- V/µs, taxa de recuperação dielétrica
  U0_dielec    {dflt: 690.0}        -- V, tensão residual imediatamente após corte
  T_bounce     {dflt: 5.0e-4}       -- s, tempo de rebote mecânico
  T_open       {dflt: 0.05}         -- s, instante de comando de abertura
  Seed         {dflt: 1}            -- semente RNG

INPUT
  i_branch                          -- corrente instantânea (A)
  v_branch                          -- tensão na chave (V)

OUTPUT
  switch_cmd                        -- 1=fechada, 0=aberta
  reign_count                       -- contador de reignições

VAR
  state         {dflt: 1}           -- 1=fechada, 0=aberta, 2=reignindo
  t_contact     {dflt: -1}          -- instante do último corte
  i_last                            -- amostra anterior de i_branch
  I_chop_rnd                        -- I_chop amostrado nesta simulação
  didt_crit_t                       -- di/dt crítico no instante atual
  U_dielec_t                        -- tensão de suportabilidade atual
  zero_cross                        -- flag: 1 se cruzou zero neste passo

INIT
  -- Inicialização: chave fechada em t=0.
  state       := 1
  switch_cmd  := 1.0
  reign_count := 0
  t_contact   := -1.0
  i_last      := 0.0
  -- Amostragem única de I_chop para esta realização (Monte Carlo).
  I_chop_rnd  := I_chop_mean + I_chop_sigma * normal(Seed)
ENDINIT

EXEC
  -- Detecta cruzamento por zero da corrente.
  zero_cross := 0
  IF (i_last * i_branch < 0) THEN
    zero_cross := 1
  ENDIF

  -- Estado 1: FECHADA — aguarda comando de abertura em T_open.
  IF (state = 1 AND t >= T_open) THEN
    -- Abrir no próximo zero-cross com corrente < I_chop_rnd.
    IF (zero_cross = 1) AND (abs(i_branch) < I_chop_rnd) THEN
      -- Testa di/dt crítico para decidir se reignita imediatamente.
      didt_crit_t := didt_crit_0 + didt_sigma * (t - T_open) * 1e6
      IF (abs((i_branch - i_last) / timestep) > (didt_crit_t * 1e6)) THEN
        -- Reignição imediata por di/dt excessivo.
        reign_count := reign_count + 1
        -- Permanece fechada.
      ELSE
        -- Corte bem-sucedido.
        state      := 0
        t_contact  := t
        switch_cmd := 0.0
      ENDIF
    ENDIF
  ENDIF

  -- Estado 0: ABERTA — testa recuperação dielétrica.
  IF (state = 0) THEN
    -- Tensão de suportabilidade cresce linearmente.
    U_dielec_t := U0_dielec + k_dielec * (t - t_contact) * 1e6
    IF (abs(v_branch) > U_dielec_t) THEN
      -- Breakdown dielétrico → reignição.
      state       := 1
      switch_cmd  := 1.0
      reign_count := reign_count + 1
    ENDIF
    -- Estabilização após T_bounce.
    IF ((t - t_contact) > T_bounce) THEN
      -- Chave permanece aberta definitivamente (fim das reignições
      -- possíveis) — a recuperação dielétrica venceu o TRV.
    ENDIF
  ENDIF

  -- Atualiza amostra anterior para próxima iteração.
  i_last := i_branch
ENDEXEC
ENDMODEL
