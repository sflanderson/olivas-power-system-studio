<Qucs Schematic 0.0.19>
<Properties>
  <View=0,0,900,500,1,0,0>
  <Grid=10,10,1>
  <DataSet=nbr17227_example.dat>
  <DataDisplay=nbr17227_example.dpl>
  <OpenDisplay=1>
  <Script=nbr17227_example.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=NBR 17227:2025 — Arc-flash em Switchgear 13.8 kV>
  <FrameText1=>
  <FrameText2=>
  <FrameText3=>
</Properties>
<Symbol>
</Symbol>
<Components>
  <Vac UTL_138 1 100 250 18 -26 0 1 "138 kV" 1 "60" 0 "0" 0 "0" 0 "1500" 0>
  <BUS BUS_HV 1 250 250 -28 -52 0 0 "BUS-138" 1 "138" 1 "3" 0 "swgr_15kv" 0 "1" 0 "0" 0 "10" 0 "4" 0 "Lado AT" 0>
  <Tr TR1 1 450 250 -26 50 0 0 "138" 0 "13.8" 0 "30" 0 "60" 0 "8.5" 0>
  <BUS SWGR_138 1 700 250 -28 -52 0 0 "SWGR-13.8" 1 "13.8" 1 "3" 0 "swgr_15kv" 1 "1" 0 "0" 0 "10" 0 "4" 0 "Switchgear MT BR" 0>
  <GND * 1 100 320 0 0 0 0>
</Components>
<Wires>
  <130 250 230 250 "" 0 0 0>
  <270 250 420 230 "VHV" 0 0 0>
  <480 230 680 250 "" 0 0 0>
  <720 250 850 250 "VSWGR" 0 0 0>
  <100 320 100 320 "" 0 0 0>
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
  <Text 100 50 12 #0000ff 0 "ABNT NBR 17227:2025 — Arc-flash 13.8 kV switchgear">
  <Text 80 100 10 #000000 0 "Sistema típico industrial brasileiro">
  <Text 80 120 10 #000000 0 "TR 138/13.8 kV — 30 MVA / uk = 8.5%">
  <Text 80 140 10 #000000 0 "Switchgear MT classe 15 kV — VCB típico">
  <Text 80 160 10 #000000 0 "Falta franca 18 kA / T_clearing 200 ms">
  <Text 80 360 10 #aa0000 0 "Critério NBR 17227 §6 (NFPA 70E:2024 Cat 130.5):">
  <Text 80 380 10 #aa0000 0 "  E ≈ 18 cal/cm² → Categoria PPE 3">
  <Text 80 400 10 #aa0000 0 "  EPI mínimo: 25 cal/cm² ARC">
  <Text 80 420 10 #00aa00 0 "  Recomendação: AFD reduz para Cat 0/1 (T=10ms)">
</Paintings>
