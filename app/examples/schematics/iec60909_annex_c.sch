<Qucs Schematic 0.0.19>
<Properties>
  <View=0,0,900,500,1,0,0>
  <Grid=10,10,1>
  <DataSet=iec60909_annex_c.dat>
  <DataDisplay=iec60909_annex_c.dpl>
  <OpenDisplay=1>
  <Script=iec60909_annex_c.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=IEC 60909-0:2016 Annex C — SC com transformador refletido>
  <FrameText1=>
  <FrameText2=>
  <FrameText3=>
</Properties>
<Symbol>
</Symbol>
<Components>
  <Vac UTILITY 1 100 250 18 -26 0 1 "110 kV" 1 "60" 0 "0" 0 "0" 0 "1500" 0>
  <BUS BUS_HV 1 250 250 -28 -52 0 0 "BUS-110" 1 "110" 1 "3" 0 "swgr_15kv" 0 "1" 0 "0" 0 "12" 0 "4" 0 "Lado HV" 0>
  <Tr TR1 1 450 250 -26 50 0 0 "110" 0 "20" 0 "25" 0 "60" 0 "12" 0>
  <BUS BUS_LV 1 650 250 -28 -52 0 0 "BUS-20" 1 "20" 1 "3" 0 "swgr_15kv" 0 "1" 0 "0" 0 "10" 0 "4" 0 "Lado LV — bus de falta" 0>
  <GND * 1 100 320 0 0 0 0>
</Components>
<Wires>
  <130 250 230 250 "VHV" 0 0 0>
  <270 250 420 230 "" 0 0 0>
  <480 230 630 250 "" 0 0 0>
  <670 250 800 250 "VLV" 0 0 0>
  <100 320 100 320 "" 0 0 0>
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
  <Text 150 50 12 #0000ff 0 "IEC 60909-0:2016 Annex C — Sistema com Transformador">
  <Text 70 100 10 #000000 0 "Concessionária 110 kV — S_kQ = 1500 MVA, R/X = 0.10">
  <Text 70 120 10 #000000 0 "TR 110/20 kV — S = 25 MVA, uk = 12%">
  <Text 70 360 10 #aa0000 0 "Falta trifásica @ 20 kV → Ik''3 ≈ 5.74 kA">
  <Text 70 380 10 #00aa00 0 "Z_total = Z_Q (refletida) + Z_T = 2.213 Ω">
  <Text 380 290 9 #aa00aa 0 "uk=12%">
  <Text 380 305 9 #aa00aa 0 "S=25 MVA">
</Paintings>
