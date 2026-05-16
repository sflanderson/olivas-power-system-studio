"""
app.preprocessor.spec.registry — registry em memória de ComponentSpecs.

Carrega um diretório de arquivos ``.ocomp`` para um dicionário em
memória indexado por ``code``.

Uso típico
----------
.. code-block:: python

    from app.preprocessor.spec import ComponentSpecRegistry
    from pathlib import Path

    reg = ComponentSpecRegistry()
    n = reg.load_directory(Path("app/preprocessor/catalog_specs"))
    print(f"Carregados {n} specs")

    r_spec = reg.get("R")
    assert r_spec is not None

Integração com ``catalog.py`` legado
------------------------------------
O :mod:`app.preprocessor.catalog` mantém a API antiga (``get(code)`` →
``CatalogEntry``) para compat, mas a partir de v0.21.8 passa a delegar
ao registry internamente. Componentes sem ``.ocomp`` correspondente
continuam a funcionar via ``_ENTRIES`` legado até a migração completa.
"""

from __future__ import annotations

from pathlib import Path

from app.preprocessor.spec.loader import load_ocomp_file
from app.preprocessor.spec.models import ComponentSpec


class ComponentSpecRegistry:
    """
    Registry em memória de ``ComponentSpec``s indexado por ``code``.

    Thread-safety: não é thread-safe. Carregar uma vez no startup e
    consultar read-only depois é o padrão.
    """

    def __init__(self) -> None:
        self._by_code: dict[str, ComponentSpec] = {}

    # ------------------------------------------------------------------
    # Carregamento
    # ------------------------------------------------------------------

    def load_directory(
        self,
        directory: str | Path,
        *,
        pattern: str = "*.ocomp",
        raise_on_error: bool = True,
    ) -> int:
        """
        Carrega todos os arquivos ``*.ocomp`` de um diretório.

        Parameters
        ----------
        directory:
            Diretório a escanear (não-recursivo).
        pattern:
            Glob pattern (default ``"*.ocomp"``).
        raise_on_error:
            Se True (default), propaga exceção no primeiro erro. Se
            False, pula arquivos com erro e retorna apenas o sucesso.

        Returns
        -------
        int
            Número de specs carregados com sucesso.

        Raises
        ------
        FileNotFoundError
            Se o diretório não existir.
        """
        d = Path(directory)
        if not d.is_dir():
            raise FileNotFoundError(f"diretório de specs não encontrado: {d}")

        count = 0
        for path in sorted(d.glob(pattern)):
            try:
                spec = load_ocomp_file(path)
                self.register(spec, path=path)
                count += 1
            except Exception:
                if raise_on_error:
                    raise
                # Modo silencioso: pula o arquivo com erro
                continue
        return count

    def register(
        self,
        spec: ComponentSpec,
        *,
        path: Path | None = None,
    ) -> None:
        """
        Registra um ``ComponentSpec`` no registry.

        Parameters
        ----------
        spec:
            Spec a registrar.
        path:
            Caminho de origem (apenas para mensagem de erro em caso de
            colisão de código).

        Raises
        ------
        ValueError
            Se já existe um spec com o mesmo ``code``.
        """
        existing = self._by_code.get(spec.code)
        if existing is not None and existing is not spec:
            src = f" (em {path})" if path else ""
            raise ValueError(
                f"colisão de código: {spec.code!r} já registrado; "
                f"tentativa de duplicação{src}"
            )
        self._by_code[spec.code] = spec

    def clear(self) -> None:
        """Remove todos os specs do registry."""
        self._by_code.clear()

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------

    def get(self, code: str) -> ComponentSpec | None:
        """Retorna o spec com o código dado, ou None."""
        return self._by_code.get(code)

    def require(self, code: str) -> ComponentSpec:
        """
        Retorna o spec com o código dado ou levanta ``KeyError``.

        Útil em código que não tolera componente desconhecido.
        """
        spec = self._by_code.get(code)
        if spec is None:
            raise KeyError(f"componente não registrado: {code!r}")
        return spec

    def contains(self, code: str) -> bool:
        """True se o código está registrado."""
        return code in self._by_code

    def all_codes(self) -> tuple[str, ...]:
        """Tupla imutável com todos os códigos registrados, ordenados."""
        return tuple(sorted(self._by_code.keys()))

    def all_specs(self) -> tuple[ComponentSpec, ...]:
        """Tupla imutável com todos os specs, ordenados por código."""
        return tuple(self._by_code[c] for c in sorted(self._by_code.keys()))

    def by_category(self, category: str) -> tuple[ComponentSpec, ...]:
        """Retorna specs filtrados por categoria, ordenados por código."""
        return tuple(
            s for s in self.all_specs() if s.category == category
        )

    def __len__(self) -> int:
        return len(self._by_code)

    def __contains__(self, code: object) -> bool:
        return isinstance(code, str) and code in self._by_code

    def __iter__(self):
        return iter(self.all_specs())
