# Olivas Power System Studio — Build de Distribuição

Specs e script de build para gerar bundles standalone Pro e Community
do Olivas Power System Studio.

## Pré-requisitos

```bash
pip install pyinstaller
```

## Edições

| Edição | Spec | Bundle name | Distribuição |
|--------|------|-------------|--------------|
| **Pro** | `build/olivas_pro.spec` | `OlivasPSS-Pro` | Hotmart / ML (EULA proprietária) |
| **Community** | `build/olivas_community.spec` | `OlivasPSS-Community` | GitHub Releases (Apache 2.0) |

### Diferença runtime

* **Pro**: `current_tier()` consulta `license_server_client` →
  destrava features pagas quando JWT válido (audit trail SHA256,
  PDF profissional, Monte Carlo, AI laudo).
* **Community**: runtime hook seta `OLIVAS_BUILD_EDITION=community`
  no env, forçando `current_tier()` a sempre retornar `educational`
  → features Pro permanecem bloqueadas.

Garantias na build:

* Ambos os bundles **excluem** explicitamente:
  - `app/core/GNUATP/` (binários ATP, não-redistribuíveis)
  - `pre-processor/` (Qucs GPL v2 — agregação separada)
  - `_tmp_ptw/`, `LIB/PTW_MANUAL/`, `LIBRARY/` (proprietários)
  - `library_relay/SEL/` (manuais SEL não-redistribuíveis)
  - `restore_points/`, `runs/` (artefatos de dev)

## Build

```bash
# Apenas edição Pro
python build/build_distribution.py --edition pro

# Apenas Community
python build/build_distribution.py --edition community

# Ambas em sequência
python build/build_distribution.py --edition both

# Com limpeza prévia
python build/build_distribution.py --edition pro --clean
```

Saída:

```
dist/
├── OlivasPSS-Pro/
│   ├── OlivasPSS-Pro.exe     (Windows; nome do binário difere por OS)
│   ├── _internal/
│   │   ├── PySide6/...
│   │   ├── matplotlib/...
│   │   └── app/...
│   └── app/resources/        (logo, ícones)
└── OlivasPSS-Community/
    └── (mesma estrutura)
```

Tamanho típico: **180–250 MB** por edição (PySide6 + matplotlib + numpy).

## Validação automática clean-room

O script `build_distribution.py` faz `rglob` no bundle gerado e
**aborta com exit code 2** se encontrar qualquer caminho proibido.
Lista verificada:

* `GNUATP`, `pre-processor`, `_tmp_ptw`, `PTW_MANUAL`, `LIBRARY`,
  `library_relay/SEL`, `restore_points`, `runs`.

Isto é o último gate antes do upload para Hotmart/ML.

## Distribuição ao cliente

### Pro (cliente pagante)

1. Cliente compra no Hotmart → webhook gera chave → e-mail envia
   link para `OlivasPSS-Pro.zip` + chave.
2. Cliente extrai, roda `OlivasPSS-Pro.exe`.
3. Menu Ajuda → "Ativar Licença..." (Ctrl+L) → cola chave → tier
   destravado.

### Community (gratuito)

1. Cliente baixa de GitHub Releases.
2. Extrai, roda `OlivasPSS-Community.exe`.
3. Tier sempre `educational` — features Pro mostradas como
   "upgrade necessário".

## Notas técnicas

* **ATP solver não é empacotado** — usuário configura caminho via
  `Simulação → Configurar caminho ATP` (Pro) ou trabalha apenas com
  análises não-ATP (Community).
* **UPX desabilitado** — evita antivirus false-positive em Windows
  Defender (custou ~30 MB extra mas evita warnings desnecessários).
* **Assinatura de código** (codesign / Authenticode) deferida para
  Sprint 4 — requer certificado EV (~R$ 1.500/ano).

## Troubleshooting

**`cannot import name X`**: adicionar `Y.X` em `hiddenimports` no
spec da edição respectiva.

**Bundle muito grande**: revisar `excludes` no spec. Qt modules
não usados são os maiores ofensores.

**Violação clean-room detectada**: arquivo proibido foi incluído
indiretamente. Adicionar caminho em `FORBIDDEN_PATHS_IN_BUNDLE` no
spec e refazer.

## Próximos passos (deferidos)

* **Sprint 4**: code signing (Authenticode em Windows, codesign em macOS).
* **Sprint 4**: auto-update via `app/gui/update_checker.py` consumindo
  manifest em CDN.
* **Sprint 5**: instalador MSI (Windows) + DMG (macOS) via Inno Setup /
  create-dmg.

---

Documento canônico de build. Atualizar a cada mudança em spec ou
em FORBIDDEN_PATHS_IN_BUNDLE.
