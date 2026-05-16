from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class RunResult:
    success: bool
    return_code: int = 0
    stdout: str = ""
    stderr: str = ""
    message: str = ""
    run_dir: str = ""
    log_file: str = ""


# Output extensions that ATP may generate
_ATP_OUTPUT_EXTS = (".pl4", ".PL4", ".lis", ".LIS", ".pch", ".PCH", ".dbg", ".DBG")


class AtpRunner:
    def __init__(self, executable_path: Optional[str] = None, timeout: int = 120):
        self.executable_path = executable_path
        self.timeout = timeout
        # v0.28.3-PRO Onda 3.1: rastreia subprocess ativo p/ kill
        self._active_process: Optional[subprocess.Popen] = None

    def is_configured(self) -> bool:
        if not self.executable_path:
            return False
        return Path(self.executable_path).is_file()

    def _stream_subprocess(
        self, proc, timeout, *,
        stdout_callback=None, stderr_callback=None,
    ):
        """
        v0.60: drena Popen.stdout/stderr line-by-line em
        threads, chamando callbacks em tempo real. Retorna
        ``(stdout_bytes, stderr_bytes)`` ao final.

        Em caso de timeout, mata o subprocess + raise.
        """
        import threading
        import time

        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []

        def _reader(stream, chunks, callback):
            try:
                for line in iter(stream.readline, b""):
                    if not line:
                        break
                    chunks.append(line)
                    if callback is not None:
                        try:
                            decoded = line.decode(
                                "latin-1", errors="replace",
                            ).rstrip()
                            callback(decoded)
                        except Exception:
                            pass    # callback errors não devem matar reader
            finally:
                try:
                    stream.close()
                except OSError:
                    pass

        t_out = threading.Thread(
            target=_reader,
            args=(proc.stdout, stdout_chunks, stdout_callback),
            daemon=True,
        )
        t_err = threading.Thread(
            target=_reader,
            args=(proc.stderr, stderr_chunks, stderr_callback),
            daemon=True,
        )
        t_out.start()
        t_err.start()

        # Espera processo terminar com timeout
        start = time.time()
        while proc.poll() is None:
            if timeout is not None and (time.time() - start) > timeout:
                proc.kill()
                t_out.join(timeout=2)
                t_err.join(timeout=2)
                raise subprocess.TimeoutExpired(proc.args, timeout)
            time.sleep(0.05)

        t_out.join(timeout=2)
        t_err.join(timeout=2)

        return (b"".join(stdout_chunks), b"".join(stderr_chunks))

    def kill_process(self) -> bool:
        """
        v0.28.3-PRO Onda 3.1: cancela simulação ATP em execução
        (chamada da GUI quando usuário clica Cancel).

        Returns
        -------
        bool
            True se um processo foi morto; False se não havia
            execução ativa.
        """
        proc = self._active_process
        if proc is None:
            return False
        try:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            return True
        except (OSError, AttributeError):
            return False

    def run(
        self, atp_file_path: str,
        timeout: Optional[int] = None,
        *,
        stdout_callback=None,
        stderr_callback=None,
        phase_callback=None,
    ) -> RunResult:
        """
        Executa o ATP. Quando ``stdout_callback`` / ``stderr_callback``
        fornecidos, recebem cada linha em tempo real.

        v0.60: live streaming via thread reader (em vez de
        ``Popen.communicate()`` que bloqueia até fim).

        v0.91.5: ``phase_callback(phase_id: str)`` recebe
        notificações de cada fase do pipeline:

        * ``"validating"`` — checando exe + atp paths
        * ``"creating_run_dir"`` — mkdir runs/<caso>_<ts>/
        * ``"copying_atp"`` — copiando .atp para exe dir
        * ``"launching"`` — pré-Popen (kill any previous)
        * ``"running"`` — Popen feito, subprocess executando
        * ``"collecting_outputs"`` — coletando .pl4/.lis
        * ``"saving_log"`` — gravando execution.log
        * ``"done"`` — final OK

        Útil para UI mostrar EXATAMENTE em qual etapa o código
        está, facilitando debug de freezes.
        """
        def _phase(p: str) -> None:
            if phase_callback is not None:
                try:
                    phase_callback(p)
                except Exception:
                    pass

        _phase("validating")
        effective_timeout = timeout if timeout is not None else self.timeout

        if not self.executable_path:
            return RunResult(
                success=False,
                message="ATP executable path not configured.",
            )

        exe_path = Path(self.executable_path)
        if not exe_path.is_file():
            return RunResult(
                success=False,
                message=f"ATP executable not found: {self.executable_path}",
            )

        atp_path = Path(atp_file_path).resolve()
        if not atp_path.is_file():
            return RunResult(
                success=False,
                message=f"ATP file not found: {atp_file_path}",
            )

        # SIM-002: create run directory
        _phase("creating_run_dir")
        run_dir = self._create_run_dir(atp_path)
        exe_dir = exe_path.parent

        # ATP needs STARTUP and support files in its cwd.
        # Strategy: copy .atp to exe dir, run there, copy results back.
        _phase("copying_atp")
        atp_copy = exe_dir / atp_path.name
        copied = False
        try:
            if atp_copy.resolve() != atp_path:
                shutil.copy2(str(atp_path), str(atp_copy))
                copied = True
        except OSError:
            pass  # If copy fails, try with absolute path anyway

        # Clean any old output files in exe_dir for this case name
        stem = atp_path.stem
        self._clean_outputs(exe_dir, stem)

        try:
            # Run ATP from its own directory (where STARTUP lives).
            # v0.28.3-PRO Onda 3.1: usa Popen para track + cancel.
            # v0.60: live streaming via thread reader.
            _phase("launching")
            run_target = atp_copy.name if copied else str(atp_path)
            # v0.91.2: ``bufsize=1`` (line buffering) só faz sentido em
            # modo texto. Em binário (stdout=PIPE → bytes), Python
            # emite RuntimeWarning e usa default buffering. Remoção
            # silencia o warning sem alterar comportamento — nosso
            # reader em ``_stream_subprocess`` chama ``readline()``
            # que retorna linha por linha independente do bufsize.
            self._active_process = subprocess.Popen(
                [str(exe_path), run_target],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(exe_dir),
            )

            _phase("running")
            if stdout_callback is not None or stderr_callback is not None:
                # v0.60: streaming mode com threads readers
                stdout_b, stderr_b = self._stream_subprocess(
                    self._active_process,
                    timeout=effective_timeout,
                    stdout_callback=stdout_callback,
                    stderr_callback=stderr_callback,
                )
                returncode = self._active_process.returncode
            else:
                # Modo legacy: communicate síncrono
                try:
                    stdout_b, stderr_b = self._active_process.communicate(
                        timeout=effective_timeout,
                    )
                    returncode = self._active_process.returncode
                except subprocess.TimeoutExpired:
                    self._active_process.kill()
                    stdout_b, stderr_b = self._active_process.communicate()
                    raise
            self._active_process = None

            # Mock para compatibilidade com código abaixo
            class _Result:
                pass
            result = _Result()
            result.stdout = stdout_b
            result.stderr = stderr_b
            result.returncode = returncode

            # ATP may emit mixed text/binary — decode safely
            stdout = result.stdout.decode("latin-1", errors="replace")
            stderr = result.stderr.decode("latin-1", errors="replace")

            # Check for real ATP error markers in stdout
            has_atp_error = "/ERROR/" in stdout
            is_crash = result.returncode not in (0, 1)
            actual_success = result.returncode == 0 and not has_atp_error

            if is_crash:
                msg = (
                    f"ATP crashou (código 0x{result.returncode & 0xFFFFFFFF:08X}). "
                    f"Tente usar tpgigg32.exe (maior capacidade de memória)."
                )
            elif has_atp_error:
                msg = "ATP reportou erros (veja o log para detalhes)."
            elif result.returncode == 0:
                msg = "ATP executado com sucesso."
            else:
                msg = f"ATP retornou código de saída {result.returncode}."

            run_result = RunResult(
                success=actual_success,
                return_code=result.returncode,
                stdout=stdout,
                stderr=stderr,
                message=msg,
                run_dir=str(run_dir),
            )

        except subprocess.TimeoutExpired:
            run_result = RunResult(
                success=False,
                message=f"Execução ATP expirou após {effective_timeout}s.",
                run_dir=str(run_dir),
            )
        except OSError as e:
            run_result = RunResult(
                success=False,
                message=f"Falha ao iniciar ATP: {e}",
                run_dir=str(run_dir),
            )

        # Collect output files from both exe_dir and atp_dir (ATP may write to either)
        _phase("collecting_outputs")
        self._collect_outputs(exe_dir, atp_path.parent, run_dir, stem)

        # Clean up the copied .atp from exe dir
        if copied and atp_copy.is_file():
            try:
                atp_copy.unlink()
            except OSError:
                pass

        # SIM-003: save log
        _phase("saving_log")
        log_path = self._save_log(run_dir, run_result, atp_path)
        run_result.log_file = str(log_path)

        _phase("done")
        return run_result

    def _create_run_dir(self, atp_path: Path) -> Path:
        """Create a timestamped run directory next to the ATP file."""
        runs_dir = atp_path.parent / "runs"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = runs_dir / f"{atp_path.stem}_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _clean_outputs(self, directory: Path, stem: str) -> None:
        """Remove old output files from directory before a new run."""
        for ext in _ATP_OUTPUT_EXTS:
            f = directory / f"{stem}{ext}"
            if f.is_file():
                try:
                    f.unlink()
                except OSError:
                    pass

    def _collect_outputs(
        self, exe_dir: Path, atp_dir: Path, run_dir: Path, stem: str
    ) -> None:
        """Copy output files to atp_dir and run_dir.

        ATP may write outputs to exe_dir or atp_dir depending on how it
        resolves the input path. Check both locations.
        """
        for ext in _ATP_OUTPUT_EXTS:
            # Check exe_dir first
            src = exe_dir / f"{stem}{ext}"
            if src.is_file():
                try:
                    shutil.copy2(str(src), str(run_dir / src.name))
                except OSError:
                    pass
                dst = atp_dir / src.name
                if dst.resolve() != src.resolve():
                    try:
                        shutil.copy2(str(src), str(dst))
                    except OSError:
                        pass
                try:
                    src.unlink()
                except OSError:
                    pass

            # Also archive files already in atp_dir
            atp_out = atp_dir / f"{stem}{ext}"
            run_copy = run_dir / f"{stem}{ext}"
            if atp_out.is_file() and not run_copy.is_file():
                try:
                    shutil.copy2(str(atp_out), str(run_copy))
                except OSError:
                    pass

    def _save_log(self, run_dir: Path, result: RunResult, atp_path: Path) -> Path:
        """Save execution log to the run directory."""
        log_path = run_dir / "execution.log"
        lines = [
            f"Olivas Power System Studio — Execution Log",
            f"Date: {datetime.now().isoformat()}",
            f"ATP file: {atp_path}",
            f"Executable: {self.executable_path}",
            f"Timeout: {self.timeout}s",
            f"Success: {result.success}",
            f"Return code: {result.return_code}",
            f"Message: {result.message}",
            "",
            "=== STDOUT ===",
            result.stdout or "(empty)",
            "",
            "=== STDERR ===",
            result.stderr or "(empty)",
        ]
        log_path.write_text("\n".join(lines), encoding="utf-8")
        return log_path
