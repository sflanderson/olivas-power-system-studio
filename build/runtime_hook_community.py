"""
runtime_hook_community.py — runtime hook do bundle Community.

Executado ANTES de qualquer import do app. Sinaliza que esta é
a edição Community, forçando ``feature_gates.current_tier()``
a retornar ``"educational"`` mesmo se houver um JWT cacheado.

Implementação: define a env var ``OLIVAS_BUILD_EDITION=community``
ANTES do `app.commercial.feature_gates` ser carregado. O módulo
``feature_gates`` lê essa flag em ``current_tier()`` e curto-circuita.

Isso garante que:
* O bundle Community não destrava features Pro nem se o usuário
  tentar enganar QSettings com tokens antigos.
* A diferenciação Community ↔ Pro é determinada no momento da
  build, não em runtime.
"""

import os

os.environ["OLIVAS_BUILD_EDITION"] = "community"
