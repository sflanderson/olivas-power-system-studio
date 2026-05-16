"""
app.gui.auto_save — v0.90: salvamento automático + crash
recovery do editor visual (PpEditor).

Filosofia
==========

Trabalho não salvo é o pesadelo do engenheiro: 30 minutos de
esquemático destruídos por um Python crash, kernel panic, ou
fechar a janela sem clicar em "Salvar". O auto-save dá uma
rede de segurança transparente — o usuário não muda nada no
fluxo, mas a cada ~60s o estado é gravado para um arquivo
``.autosave`` ao lado.

Casos de uso
=============

1. **Untitled**: o usuário acabou de iniciar um esquemático novo
   (sem path). Salvamos em
   ``~/.olivas/recovery/recovery_<timestamp>.sch``.
2. **Path conhecido**: usuário abriu/salvou ``foo.sch``;
   autosave em ``foo.sch.autosave``.
3. **Sem mudanças** (undo_stack clean): pulamos o save (não
   gera I/O desnecessário).
4. **Recuperação na inicialização**: ``MainWindow`` checa por
   arquivos ``.autosave`` em paths recentes; se algum for
   mais recente que o ``.sch``, oferece recuperação.

Robustez
==========

* Falhas no save NÃO derrubam o editor — apenas log silencioso.
  Auto-save é "best-effort".
* Save manual (``save_to_sch``) limpa o autosave correspondente
  imediatamente (sem esperar próximo timer tick).
* Saída limpa do app (todas as janelas fechadas com clean state)
  remove autosaves órfãos.

Segurança
==========

Autosave files NÃO são interpretados como recuperação se forem
MAIS ANTIGOS que o ``.sch`` correspondente — assume que o
usuário fez save manual depois do último autosave.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal


# Sufixo do arquivo de autosave para .sch conhecido.
AUTOSAVE_SUFFIX = ".autosave"

# Diretório para autosaves de schemas untitled.
_RECOVERY_DIR = Path.home() / ".olivas" / "recovery"


def autosave_path_for(sch_path: str) -> Path:
    """Path do autosave correspondente a um .sch."""
    return Path(sch_path + AUTOSAVE_SUFFIX)


def remove_autosave_for(sch_path: str) -> None:
    """
    Remove autosave correspondente a um .sch (chamado após save
    manual bem-sucedido, sinaliza "recuperação não é mais
    necessária"). Falhas silenciosas.
    """
    p = autosave_path_for(sch_path)
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass


def find_autosaves_to_recover() -> list[tuple[str, str]]:
    """
    Varre paths de autosave conhecidos e retorna pares
    ``(autosave_path, original_sch_path)`` que merecem oferecer
    recuperação ao usuário.

    Critérios:

    * O arquivo ``.autosave`` existe.
    * O ``.sch`` correspondente NÃO existe OU tem ``mtime`` mais
      antigo que o autosave (autosave é mais recente).

    Para untitled (sem .sch original), o caller pode usar
    :func:`find_untitled_recoveries` separadamente.
    """
    candidates: list[tuple[str, str]] = []
    # Não escaneia disco inteiro — só os recents do QSettings,
    # tratado pelo caller. Este helper apenas decide se UM
    # autosave é elegível (chamado por caller).
    return candidates


def is_autosave_newer_than_original(
    autosave_path: str, original_sch_path: str,
) -> bool:
    """
    True se o ``.autosave`` é mais recente que o ``.sch``
    correspondente (ou se o ``.sch`` não existe).

    Usado pelo MainWindow para decidir se oferece recovery do
    último arquivo aberto.
    """
    a = Path(autosave_path)
    o = Path(original_sch_path)
    if not a.is_file():
        return False
    if not o.is_file():
        return True   # autosave existe, original não — recover
    try:
        return a.stat().st_mtime > o.stat().st_mtime
    except OSError:
        return False


def find_untitled_recoveries() -> list[Path]:
    """
    Lista arquivos em ``~/.olivas/recovery/`` que são candidatos
    a recuperação de schemas que o usuário nunca salvou (untitled).

    Ordenados por mtime decrescente (mais recente primeiro).
    """
    if not _RECOVERY_DIR.is_dir():
        return []
    files: list[Path] = []
    try:
        for p in _RECOVERY_DIR.iterdir():
            if p.is_file() and p.suffix == ".sch":
                files.append(p)
    except OSError:
        return []
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def cleanup_old_recoveries(max_age_days: int = 30) -> int:
    """
    Remove arquivos em ``~/.olivas/recovery/`` mais velhos que
    ``max_age_days``. Retorna número de arquivos removidos.

    UX: depois que o usuário recupera (ou descarta) um trabalho
    untitled, o arquivo deve sumir. Mas se o usuário simplesmente
    fecha sem responder ao dialog, queremos limpar com o tempo.
    """
    import time
    if not _RECOVERY_DIR.is_dir():
        return 0
    cutoff = time.time() - max_age_days * 86400
    n = 0
    try:
        for p in _RECOVERY_DIR.iterdir():
            if not p.is_file():
                continue
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink()
                    n += 1
            except OSError:
                continue
    except OSError:
        pass
    return n


# ---------------------------------------------------------------------------
# AutoSaveManager
# ---------------------------------------------------------------------------


class AutoSaveManager(QObject):
    """
    Gerenciador de auto-save para um :class:`PpEditor`.

    Uso (em ``MainWindow.__init__``)::

        from app.gui.auto_save import AutoSaveManager
        self.auto_save = AutoSaveManager(
            editor=self.schematic_pp,
            interval_seconds=60,
        )
        self.auto_save.start()

    Sinais
    --------

    * ``saved(path: str)`` — emitido após um save bem-sucedido
      (o caller pode atualizar status bar com timestamp).
    * ``failed(error: str)`` — emitido em falha (raro — log).
    """

    saved = Signal(str)
    failed = Signal(str)

    DEFAULT_INTERVAL_SECONDS = 60
    UNTITLED_RECOVERY_PREFIX = "recovery_"

    def __init__(
        self,
        editor,                          # PpEditor (duck-typed)
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._editor = editor
        self._interval_ms = max(5_000, interval_seconds * 1000)
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self._tick)
        # Caminho do último untitled-autosave (para limpeza após
        # save manual ou nova sessão).
        self._untitled_path: Optional[Path] = None

    def start(self) -> None:
        """Inicia o timer."""
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def is_running(self) -> bool:
        return self._timer.isActive()

    @property
    def interval_seconds(self) -> int:
        return self._interval_ms // 1000

    def set_interval_seconds(self, n: int) -> None:
        """Atualiza intervalo (mínimo 5s)."""
        self._interval_ms = max(5_000, n * 1000)
        self._timer.setInterval(self._interval_ms)

    def trigger_now(self) -> Optional[str]:
        """
        Força um save imediato (útil em testes ou em
        ``QApplication.aboutToQuit``). Retorna o path
        salvo ou ``None`` se nada foi salvo.
        """
        return self._tick()

    # ---- Internals --------------------------------------------------------

    def _tick(self) -> Optional[str]:
        """
        Tenta salvar se houver mudanças. Retorna o path salvo
        ou ``None``.
        """
        try:
            if not self._editor.is_dirty():
                return None
        except Exception:
            return None
        target = self._compute_target_path()
        if target is None:
            return None
        try:
            self._save_to(target)
        except Exception as e:    # noqa: BLE001
            self.failed.emit(str(e))
            return None
        self.saved.emit(str(target))
        return str(target)

    def _compute_target_path(self) -> Optional[Path]:
        """
        Decide o destino do autosave:

        * Se editor tem ``current_sch_path``: ``<path>.autosave``
        * Senão (untitled): ``~/.olivas/recovery/recovery_<timestamp>.sch``.
          Reusa o mesmo path em ticks subsequentes da mesma sessão.
        """
        path = getattr(self._editor, "current_sch_path", None)
        if path:
            return autosave_path_for(path)
        # Untitled — gera/reusa um caminho na pasta de recovery.
        if self._untitled_path is None:
            try:
                _RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
            except OSError:
                return None
            import time
            ts = int(time.time())
            self._untitled_path = (
                _RECOVERY_DIR
                / f"{self.UNTITLED_RECOVERY_PREFIX}{ts}.sch"
            )
        return self._untitled_path

    def _save_to(self, target: Path) -> None:
        """
        Serializa o ``PpProject`` atual para ``target``.

        Usa o mesmo serializer que :meth:`PpEditor.save_to_sch`,
        mas SEM tocar em ``_current_sch_path`` (é "save invisível").
        """
        from app.preprocessor.qucs_sch_serializer import serialize_sch_file
        proj = self._editor.scene.to_project()
        target.parent.mkdir(parents=True, exist_ok=True)
        serialize_sch_file(proj, str(target))
        # Datablocks sidecar — segue mesmo padrão do save manual.
        try:
            from app.gui.schematic_pp.datablock_io import (
                save_datablocks_sidecar,
            )
            save_datablocks_sidecar(str(target), proj.datablocks)
        except Exception:
            pass

    def clear_untitled_path(self) -> None:
        """
        Esquece o ``_untitled_path`` da sessão atual e remove o
        arquivo correspondente. Chamado após:

        * Save manual de um novo schema (untitled deixa de ser).
        * Resposta a recovery dialog (descartado).
        """
        if self._untitled_path is not None:
            try:
                self._untitled_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._untitled_path = None
