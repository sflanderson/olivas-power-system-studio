"""
app.postprocessor — análise de resultados de simulação ATP-EMTP.

Cada submódulo consome dados de:

1. **Saída do ATP** (PL4 binário) — quando disponível.
2. **Pré-cálculos do Olivas** (synchronous_machine.short_circuit_
   currents, lcc.compute_propagation, etc.).
3. **Normas técnicas** (``app.standards``) — referências
   numéricas para comparação e relatórios.

Submódulos planejados:

* ``trt_analyzer`` — TRT (Transient Recovery Voltage) vs IEC
  62271-100 envelopes (v0.27.1).
* ``short_circuit`` — cálculos IEC 60909-0 (Ik'', Ip, Idc, Ib)
  (v0.27.2).
* ``arc_flash`` — energia incidente NBR 17227 / IEEE 1584-2018
  (v0.27.3).
* ``relay_coordination`` — TC curves IEC 60255 + ANSI device
  numbers (v0.27.4).
"""
