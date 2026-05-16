"""
app.gui.howto_dialog — dialog "Como executar?" acessível
via F1.

v0.92.2 — Reescrito para o **Olivas Power System Studio**:
foco em análise (SC/PF/Coord/Arc-flash/Balanço). Integração
ATP foi desvinculada na v0.92.1 e não é mais um caminho de
execução do app principal.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout,
)


_HOWTO_HTML = """
<h2>Como executar um estudo?</h2>

<p><b>Olivas Power System Studio</b> oferece dois caminhos:</p>

<h3>1. ▶ Executar Análise (estudos profissionais)</h3>

<p>Modele o unifilar no <b>Esquemático Visual</b> e clique em
<b>▶ Executar Análise</b> na toolbar (ou menu <b>Análise</b>).</p>

<table border="1" cellpadding="4" cellspacing="0">
<tr style="background:#eee;">
  <th>Análise</th>
  <th>Pré-requisitos</th>
  <th>Norma</th>
</tr>
<tr>
  <td><b>Estudo completo do barramento</b></td>
  <td>BUS no esquemático</td>
  <td>IEC 60909 + IEEE 1584 + NBR 17227 + IEEE 242</td>
</tr>
<tr>
  <td>Curto-circuito</td>
  <td>BUS conectado a fonte (Vac/SM/Tr)</td>
  <td>IEC 60909-0:2016</td>
</tr>
<tr>
  <td>Fluxo de potência</td>
  <td>Topologia + Slack/PV/PQ</td>
  <td>IEEE 399 / Newton-Raphson</td>
</tr>
<tr>
  <td>Coordenação e seletividade</td>
  <td>Cadeia upstream/downstream com relés</td>
  <td>IEEE 242 Buff Book §15</td>
</tr>
<tr>
  <td>Energia incidente / Arc-flash</td>
  <td>BUS + tempo de extinção</td>
  <td>NBR 17227 / IEEE 1584</td>
</tr>
<tr>
  <td>Balanço de carga / partida de motor</td>
  <td>BUS + MOTOR</td>
  <td>IEEE 141 Red Book / IEEE 399 §10</td>
</tr>
</table>

<h3>2. 📚 Exemplos das normas</h3>

<p>Menu <b>Exemplos</b> oferece 6 worked examples com
esquemáticos pré-preenchidos:</p>
<ul>
  <li>Stevenson §9 — Power Flow 3-bus</li>
  <li>Stevenson §11 — Faltas Assimétricas</li>
  <li>IEC 60909 Annex C — SC com transformador</li>
  <li>IEEE 1584 D.4 — Arc-flash 480V VCB</li>
  <li>IEEE 399 §10 — Partida Motor 1500 kW</li>
  <li>NBR 17227 — Switchgear 13.8 kV</li>
</ul>

<p>Cada exemplo carrega o esquemático no editor visual,
executa o cálculo e exibe relatório expected vs computed.</p>

<h3>O que é "BUS"?</h3>

<p>O <b>componente BUS</b> representa um barramento elétrico
estilo PTW Power*Tools — <b>linha grossa contínua</b> com:</p>
<ul>
  <li>Multi-conexão em qualquer ponto (a cada 10 px de grid)</li>
  <li>Redimensionável arrastando os handles azuis quando
      selecionado (range 60-4000 px)</li>
  <li>Metadata para arc-flash:
    <ul>
      <li>V_LL (kV)</li>
      <li>Tipo de painel (CCM, switchgear, LV panel)</li>
      <li>Lineside vs loadside</li>
      <li>AFD (Arc Flash Detection) — reduz tempo de extinção
          para ~10 ms</li>
    </ul>
  </li>
</ul>

<p>Adicione via <b>Paleta → BUS</b>, ou pelos templates do
Welcome dialog.</p>

<h3>Auditabilidade dos laudos</h3>

<p>Todos os relatórios incluem:</p>
<ul>
  <li><b>SHA256 dos inputs</b> — fingerprint para
      rastreabilidade entre versões.</li>
  <li><b>Timestamp ISO 8601</b> imutável.</li>
  <li><b>Bloco de responsabilidade técnica</b> (engenheiro,
      CREA, ART, assinatura).</li>
  <li><b>Coluna "Norma — equação"</b> em cada parâmetro
      calculado (IEC §, NBR §, IEEE §).</li>
  <li><b>Limitações declaradas</b> (heurísticas do MVP em
      bloco amarelo).</li>
</ul>

<p>Conformidade: ISO 9001 §8.5.1 (rastreabilidade),
NR-10 §10.2.4 (responsabilidade técnica), NBR 17227
§5.4.4 (assinatura do responsável).</p>

<h3>Configurar API Claude</h3>

<p>Para habilitar o assistente Claude no chat global:</p>
<ul>
  <li><b>Ferramentas → Configurar API Key Claude...</b></li>
  <li>Cole sua chave (sk-ant-...) e teste.</li>
  <li>Persistente via QSettings.</li>
</ul>

<hr>

<p><small>Pressione <b>Esc</b> ou <b>OK</b> para fechar.</small></p>
"""


class HowToDialog(QDialog):
    """Dialog modal com texto HTML explicativo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Como executar um estudo? (F1)")
        self.setMinimumSize(720, 600)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        browser = QTextBrowser()
        browser.setHtml(_HOWTO_HTML)
        browser.setOpenExternalLinks(True)
        layout.addWidget(browser)
        bb = QDialogButtonBox(QDialogButtonBox.Ok)
        bb.button(QDialogButtonBox.Ok).setText("Fechar")
        bb.accepted.connect(self.accept)
        layout.addWidget(bb)
