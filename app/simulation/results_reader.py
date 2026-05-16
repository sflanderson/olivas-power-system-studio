"""ATP simulation results reader.

Supports:
- .lis text output files
- .pl4 binary results (multiple ATP format variants)
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AtpResults:
    file_path: str = ""
    variables: list[str] = field(default_factory=list)
    time: list[float] = field(default_factory=list)
    data: dict[str, list[float]] = field(default_factory=dict)
    delta_t: float = 0.0
    n_steps: int = 0

    def get_variable(self, name: str) -> Optional[list[float]]:
        """Get data for a variable by name (case-insensitive)."""
        for vname, vdata in self.data.items():
            if vname.upper() == name.upper():
                return vdata
        return None

    def get_time_range(self) -> tuple[float, float]:
        if self.time:
            return self.time[0], self.time[-1]
        return 0.0, 0.0

    def summary(self) -> str:
        t0, t1 = self.get_time_range()
        return (
            f"PL4: {len(self.variables)} variables, "
            f"{self.n_steps} steps, "
            f"dt={self.delta_t:.2e}s, "
            f"t=[{t0:.6f}, {t1:.6f}]s"
        )


def read_pl4(filepath: str) -> AtpResults:
    """Read ATP .pl4 binary results file.

    Tries multiple format detection strategies:
    1. GNUATP direct binary (80-byte header + 16-byte var names)
    2. Fortran unformatted records (record-length markers)
    3. Alternative direct binary layout
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"PL4 file not found: {filepath}")

    results = AtpResults(file_path=str(path))

    with open(path, "rb") as f:
        raw = f.read()

    if len(raw) < 16:
        raise ValueError("PL4 file too small to contain valid data")

    # Try GNUATP format first (80-byte header, 16-byte variable names)
    try:
        _parse_pl4_gnuatp(raw, results)
        if results.n_steps > 0:
            return results
    except Exception:
        pass

    # Try Fortran unformatted format
    try:
        results = AtpResults(file_path=str(path))
        _parse_pl4_fortran(raw, results)
        if results.n_steps > 0:
            return results
    except Exception:
        pass

    # Try alternative direct binary format
    try:
        results = AtpResults(file_path=str(path))
        _parse_pl4_direct(raw, results)
        if results.n_steps > 0:
            return results
    except Exception:
        pass

    raise ValueError(
        f"Could not parse PL4 file: {filepath}. "
        f"File size: {len(raw)} bytes. "
        f"First 16 bytes: {raw[:16].hex()}"
    )


# ======================================================================
# GNUATP PL4 format
# ======================================================================

# Variable type codes in PL4 header (byte 3 of the 4-char prefix)
_PL4_TYPE_LABELS = {
    "4": "v",       # voltage
    "7": "c",       # branch current
    "8": "i",       # switch current
    "9": "TACS",    # TACS/MODELS output
    "14": "v",      # voltage (type 14)
}


def _format_pl4_varname(chunk: bytes) -> str:
    """Format a 16-byte PL4 variable name into readable form.

    Format: 4-char prefix (spaces + type digit) + 6-char node1 + 6-char node2.
    """
    prefix = chunk[:4].decode("latin-1").strip()
    node1 = chunk[4:10].decode("latin-1").strip()
    node2 = chunk[10:16].decode("latin-1").strip()

    label = _PL4_TYPE_LABELS.get(prefix, prefix)

    if node2:
        return f"{label}({node1}-{node2})"
    return f"{label}({node1})"


def _parse_pl4_gnuatp(raw: bytes, results: AtpResults) -> None:
    """Parse GNUATP PL4 format (direct binary, no Fortran markers).

    Layout:
    - 80-byte header: byte0 flag, timestamp, metadata, delta_t, t_max
    - Variable names: 16 bytes each (prefix + node1 + node2)
    - Data records: (1 + n_vars) x float32 LE per timestep
    """
    if len(raw) < 512:
        raise ValueError("File too small for GNUATP PL4")

    # Detect format: variable names start at offset 80 with space (0x20)
    if raw[80] != 0x20:
        raise ValueError("Not GNUATP format: no variable names at offset 80")

    # Read delta_t from offset 40
    results.delta_t = struct.unpack_from("<f", raw, 40)[0]
    if results.delta_t <= 0 or results.delta_t > 1:
        raise ValueError(f"Invalid delta_t: {results.delta_t}")

    # Read variable names (16 bytes each, starting at offset 80)
    offset = 80
    while offset + 16 <= len(raw):
        chunk = raw[offset:offset + 16]
        # Valid names start with space (0x20); stop at null or non-space
        if chunk[0] != 0x20:
            break
        name = _format_pl4_varname(chunk)
        results.variables.append(name)
        offset += 16

    if not results.variables:
        raise ValueError("No variables found in GNUATP PL4")

    n_vars = len(results.variables)
    data_start = offset

    # Validate: data size must be exact multiple of record size
    n_cols = 1 + n_vars
    record_bytes = n_cols * 4
    data_size = len(raw) - data_start
    if data_size % record_bytes != 0:
        raise ValueError(
            f"Data size {data_size} not multiple of record size {record_bytes}"
        )

    n_steps = data_size // record_bytes

    # Pre-allocate lists
    for var in results.variables:
        results.data[var] = []

    # Read all data records
    for step in range(n_steps):
        pos = data_start + step * record_bytes
        values = struct.unpack_from(f"<{n_cols}f", raw, pos)
        results.time.append(values[0])
        for i, var in enumerate(results.variables):
            results.data[var].append(values[i + 1])

    results.n_steps = n_steps


# ======================================================================
# Fortran unformatted PL4 format
# ======================================================================


def _parse_pl4_fortran(raw: bytes, results: AtpResults) -> None:
    """Parse PL4 with Fortran unformatted record markers.

    Fortran unformatted files have 4-byte record-length markers
    before and after each record.
    """
    offset = 0

    # --- Record 1: header with delta_t and number of variables ---
    rec1_len, offset = _read_rec_marker(raw, offset)
    if rec1_len <= 0 or rec1_len > 10000:
        raise ValueError(f"Invalid first record length: {rec1_len}")

    rec1_start = offset
    rec1_data = raw[rec1_start:rec1_start + rec1_len]

    # delta_t is first float
    if len(rec1_data) >= 4:
        results.delta_t = struct.unpack_from("<f", rec1_data, 0)[0]
        if results.delta_t <= 0 or results.delta_t > 1:
            # Try big-endian
            results.delta_t = struct.unpack_from(">f", rec1_data, 0)[0]

    # Number of variables at byte 4
    n_vars = 0
    if len(rec1_data) >= 8:
        n_vars = struct.unpack_from("<i", rec1_data, 4)[0]
        if n_vars <= 0 or n_vars > 500:
            n_vars = struct.unpack_from(">i", rec1_data, 4)[0]
        if n_vars <= 0 or n_vars > 500:
            raise ValueError(f"Unexpected n_vars: {n_vars}")

    offset = rec1_start + rec1_len
    _, offset = _read_rec_marker(raw, offset)  # end marker

    # --- Record 2: variable names ---
    rec2_len, offset = _read_rec_marker(raw, offset)
    if rec2_len > 0 and offset + rec2_len <= len(raw):
        name_data = raw[offset:offset + rec2_len]
        # Try 6-char names first, then 8-char
        for chars_per_name in (6, 8):
            n_names = rec2_len // chars_per_name
            if n_names >= n_vars:
                results.variables = []
                for i in range(n_names):
                    chunk = name_data[i * chars_per_name:(i + 1) * chars_per_name]
                    try:
                        name = chunk.decode("ascii").strip()
                        if name:
                            results.variables.append(name)
                    except UnicodeDecodeError:
                        results.variables.append(f"VAR_{i}")
                if len(results.variables) >= n_vars:
                    break

        offset += rec2_len
        _, offset = _read_rec_marker(raw, offset)  # end marker

    # --- Data records ---
    n_cols = len(results.variables) + 1  # time + variables
    for var in results.variables:
        results.data[var] = []

    while offset + 4 < len(raw):
        try:
            rec_len, new_offset = _read_rec_marker(raw, offset)
        except Exception:
            break
        offset = new_offset

        if rec_len <= 0 or offset + rec_len > len(raw):
            break

        n_floats = rec_len // 4
        if n_floats < n_cols:
            break

        values = struct.unpack_from(f"<{n_floats}f", raw, offset)
        offset += rec_len

        try:
            _, offset = _read_rec_marker(raw, offset)
        except Exception:
            break

        results.time.append(values[0])
        for i, var in enumerate(results.variables):
            if i + 1 < len(values):
                results.data[var].append(values[i + 1])

    results.n_steps = len(results.time)


# ======================================================================
# Direct binary PL4 format
# ======================================================================


def _parse_pl4_direct(raw: bytes, results: AtpResults) -> None:
    """Parse PL4 with direct binary layout (no record markers).

    Some ATP versions write a simpler format:
    - 4 bytes: n_vars (int32)
    - 4 bytes: n_steps (int32)
    - 4 bytes: delta_t (float32)
    - n_vars * 6 bytes: variable names
    - n_steps * (n_vars+1) * 4 bytes: data (float32, time + variables)
    """
    offset = 0

    n_vars = struct.unpack_from("<i", raw, offset)[0]
    offset += 4

    if n_vars <= 0 or n_vars > 500:
        raise ValueError(f"Invalid n_vars: {n_vars}")

    n_steps = struct.unpack_from("<i", raw, offset)[0]
    offset += 4

    if n_steps <= 0 or n_steps > 10_000_000:
        raise ValueError(f"Invalid n_steps: {n_steps}")

    results.delta_t = struct.unpack_from("<f", raw, offset)[0]
    offset += 4

    # Read variable names (6 chars each)
    for i in range(n_vars):
        if offset + 6 > len(raw):
            break
        chunk = raw[offset:offset + 6]
        offset += 6
        try:
            results.variables.append(chunk.decode("ascii").strip())
        except UnicodeDecodeError:
            results.variables.append(f"VAR_{i}")

    for var in results.variables:
        results.data[var] = []

    # Read data
    n_cols = n_vars + 1
    expected_data = n_steps * n_cols * 4

    if offset + expected_data > len(raw):
        # Adjust n_steps to what's actually available
        available = len(raw) - offset
        n_steps = available // (n_cols * 4)

    for step in range(n_steps):
        if offset + n_cols * 4 > len(raw):
            break
        values = struct.unpack_from(f"<{n_cols}f", raw, offset)
        offset += n_cols * 4

        results.time.append(values[0])
        for i, var in enumerate(results.variables):
            if i + 1 < len(values):
                results.data[var].append(values[i + 1])

    results.n_steps = len(results.time)


def _read_rec_marker(raw: bytes, offset: int) -> tuple[int, int]:
    """Read a 4-byte Fortran record-length marker."""
    if offset + 4 > len(raw):
        raise ValueError("Unexpected end of file reading record marker")
    val = struct.unpack_from("<i", raw, offset)[0]
    return val, offset + 4


# ======================================================================
# .lis text reader
# ======================================================================


def read_lis(filepath: str) -> str:
    """Read ATP .lis text output file and return as string."""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"LIS file not found: {filepath}")
    return path.read_text(encoding="utf-8", errors="replace")


# ======================================================================
# File discovery
# ======================================================================


def find_result_files(atp_filepath: str) -> dict[str, str]:
    """Find result files (.pl4, .lis) associated with an ATP file."""
    path = Path(atp_filepath)
    base = path.stem
    directory = path.parent

    found: dict[str, str] = {}

    for ext in (".pl4", ".PL4"):
        candidate = directory / f"{base}{ext}"
        if candidate.is_file():
            found["pl4"] = str(candidate)
            break

    for ext in (".lis", ".LIS"):
        candidate = directory / f"{base}{ext}"
        if candidate.is_file():
            found["lis"] = str(candidate)
            break

    return found
