"""
Docstring Analysis Script
=========================
Analyses generated docstrings for Python and TypeScript, detecting errors
and computing quality statistics.

Input files expected:
  - python_docstrings.json     → {"docstrings": [{"route": ..., "docstring": ...}, ...]}
  - typescript_docstrings.json → {"docstrings": [{"path":  ..., "docstring": ...}, ...]}
"""

import json
from itertools import product

import pandas as pd


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_file(filename: str) -> pd.DataFrame:
    """Load a JSON docstring file and return a flat pandas DataFrame.

    pd.read_json cannot flatten the nested {'docstrings': [...]} structure
    on its own, so the file is read with the standard json module first and
    then converted to a DataFrame.

    Parameters
    ----------
    filename : str
        Path to the JSON file.

    Returns
    -------
    pd.DataFrame
        One row per docstring entry with the original keys as columns.
    """
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return pd.DataFrame(data['docstrings'])


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def split_venv(
    df: pd.DataFrame,
    path_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate project docstrings from .venv / virtual-environment rows.

    Paths generated inside a virtual environment are noise and must be
    excluded from quality analysis.  The function is deliberately broad:
    it matches both dot-separated module paths (``.venv.Lib.site-packages…``)
    and slash-separated filesystem paths (``.venv/lib/…``).

    Parameters
    ----------
    df : pd.DataFrame
        Full DataFrame as returned by :func:`load_file`.
    path_col : str
        Column that holds the element path (``'route'`` for Python).

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        ``(project_df, venv_df)`` — both reset to a clean 0-based index.
    """
    venv_mask = df[path_col].str.contains(
        r'^\.?venv[./\\]',   # starts with  .venv.  /  venv.  /  .venv/  /  venv/
        regex=True, na=False
    )
    return (
        df[~venv_mask].reset_index(drop=True),
        df[venv_mask].reset_index(drop=True),
    )


# ---------------------------------------------------------------------------
# Error detection
# ---------------------------------------------------------------------------

def find_errors(df: pd.DataFrame, docstring_col: str = 'docstring') -> pd.DataFrame:
    """Find all erroneous docstrings and label their error type.

    Errors are defined as:

    * ``placeholder``  – the docstring still contains the literal text
      ``<placeholder>``, meaning the LLM did not substitute a real
      description and also ignored the instruction to remove placeholders.
    * ``none_only``    – the docstring is the bare string ``"None"``
      (case-insensitive, ignoring surrounding whitespace), indicating that
      the LLM found no meaningful content to describe.
    * ``null_value``   – the docstring field is JSON ``null`` / pandas NaN.
    * ``placeholder_and_none`` – both placeholder and none conditions hold
      simultaneously (edge case).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame returned by :func:`load_file`.
    docstring_col : str, optional
        Name of the column that holds the docstring text.

    Returns
    -------
    pd.DataFrame
        Subset of *df* containing only the erroneous rows, with an extra
        ``'error_type'`` column.
    """
    null_mask        = df[docstring_col].isna()
    placeholder_mask = df[docstring_col].str.contains('<placeholder>', case=False, na=False)
    none_mask        = df[docstring_col].str.strip().str.lower().eq('none')

    result = df.copy()
    result['error_type'] = pd.NA

    result.loc[placeholder_mask,             'error_type'] = 'placeholder'
    result.loc[none_mask,                    'error_type'] = 'none_only'
    result.loc[null_mask,                    'error_type'] = 'null_value'
    result.loc[placeholder_mask & none_mask, 'error_type'] = 'placeholder_and_none'

    return result[result['error_type'].notna()].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def compute_length_stats(df: pd.DataFrame, docstring_col: str = 'docstring') -> pd.Series:
    """Return descriptive length statistics (in characters) for valid docstrings.

    Parameters
    ----------
    df : pd.DataFrame
        Full docstring DataFrame (NaNs are dropped automatically).
    docstring_col : str, optional
        Column that holds the docstring text.

    Returns
    -------
    pd.Series
        Output of ``pd.Series.describe()`` on character-level lengths.
    """
    return df[docstring_col].dropna().str.len().describe()


def compute_line_quartiles(df: pd.DataFrame, docstring_col: str = 'docstring') -> pd.DataFrame:
    """Classify docstrings into line-count quartiles (mirrors the paper's analysis).

    Parameters
    ----------
    df : pd.DataFrame
        Full docstring DataFrame.
    docstring_col : str, optional
        Column that holds the docstring text.

    Returns
    -------
    pd.DataFrame
        Original DataFrame augmented with ``'line_count'`` and ``'quartile'``
        columns.
    """
    result = df.copy()
    result['line_count'] = result[docstring_col].dropna().str.count(r'\n') + 1

    line_counts = result['line_count'].dropna()
    if line_counts.empty:
        result['quartile'] = pd.NA
        return result

    # retbins=True reveals how many unique edges survived duplicates='drop',
    # so we can pass exactly (n_edges - 1) labels and avoid the ValueError.
    _, bins = pd.qcut(line_counts, q=4, duplicates='drop', retbins=True)
    n_bins  = len(bins) - 1
    labels  = ['Q1', 'Q2', 'Q3', 'Q4'][:n_bins]

    result['quartile'] = pd.qcut(
        result['line_count'], q=4,
        labels=labels,
        duplicates='drop',
    )
    return result


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

#: Column names and their human-readable short labels used in reports.
SECTION_COLS = ['has_parameters', 'has_returns', 'has_exceptions', 'has_examples']
SECTION_NAMES = ['Parameters', 'Returns', 'Exceptions', 'Examples']
SECTION_SHORT = ['Params', 'Returns', 'Except', 'Examples']


def detect_sections(df: pd.DataFrame, docstring_col: str = 'docstring') -> pd.DataFrame:
    """Add boolean columns indicating which documentation sections are present.

    Supports NumPy, Google, and TSDoc / JSDoc conventions so that the same
    function works for both Python and TypeScript docstrings.

    Section detection rules
    -----------------------
    Parameters  → ``Parameters\\n---`` (NumPy) · ``Args:`` / ``Arguments:`` (Google) · ``@param`` (TSDoc)
    Returns     → ``Returns\\n---``  (NumPy) · ``Returns:`` (Google) · ``@returns`` / ``@return`` (TSDoc)
    Exceptions  → ``Raises\\n---``   (NumPy) · ``Raises:`` (Google) · ``@throws`` / ``@exception`` (TSDoc)
    Examples    → ``Examples\\n---`` (NumPy) · ``Examples:`` (Google) · ``@example`` (TSDoc)

    Parameters
    ----------
    df : pd.DataFrame
        Docstring DataFrame (project files only — venv already excluded).
    docstring_col : str, optional
        Column that holds the docstring text.

    Returns
    -------
    pd.DataFrame
        Original DataFrame with four new boolean columns:
        ``has_parameters``, ``has_returns``, ``has_exceptions``,
        ``has_examples``.
    """
    result = df.copy()
    text   = result[docstring_col].fillna('')

    result['has_parameters'] = text.str.contains(
        r'Parameters\s*\n\s*-{3,}'   # NumPy
        r'|Args\s*:'                  # Google
        r'|Arguments\s*:'             # Google variant
        r'|@param\b',                 # TSDoc / JSDoc
        case=False, regex=True,
    )
    result['has_returns'] = text.str.contains(
        r'Returns\s*\n\s*-{3,}'      # NumPy
        r'|Returns\s*:'              # Google
        r'|@returns?\b',             # TSDoc / JSDoc
        case=False, regex=True,
    )
    result['has_exceptions'] = text.str.contains(
        r'Raises\s*\n\s*-{3,}'      # NumPy
        r'|Raises\s*:'               # Google
        r'|@throws?\b'               # TSDoc / JSDoc
        r'|@exception\b',            # JSDoc legacy
        case=False, regex=True,
    )
    result['has_examples'] = text.str.contains(
        r'Examples?\s*\n\s*-{3,}'   # NumPy
        r'|Examples?\s*:'            # Google
        r'|@example\b',              # TSDoc / JSDoc
        case=False, regex=True,
    )
    return result


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

_W = 58   # separator width


def _sep() -> str:
    return '=' * _W


def _print_section_analysis(df: pd.DataFrame, language: str) -> None:
    """Print per-section counts and the full 2⁴ intersection table.

    Parameters
    ----------
    df : pd.DataFrame
        Project docstrings with venv already excluded.
    language : str
        Display name used in the section header.
    """
    df    = detect_sections(df)
    total = len(df)
    if total == 0:
        print(f'\n  No docstrings to analyse for {language}.')
        return

    # ── Per-section presence counts ────────────────────────────────────────
    print(f'\n  Documentation Sections  —  {language}  (n = {total})')
    print(f'  {"-" * 42}')
    print(f'  {"Section":<16} {"Count":>7}  {"%":>7}')
    print(f'  {"-" * 32}')
    for col, name in zip(SECTION_COLS, SECTION_NAMES):
        n = int(df[col].sum())
        print(f'  {name:<16} {n:>7}  {n / total * 100:>6.1f} %')

    # ── 2⁴ intersection table ─────────────────────────────────────────────
    col_w  = 10
    hdr    = (
        f'  '
        + ''.join(f'{s:<{col_w}}' for s in SECTION_SHORT)
        + f'{"Count":>7}  {"%":>7}'
    )
    divider = f'  {"-" * (len(hdr) - 2)}'

    print(f'\n  All 2⁴ Intersection Sets  ( ✓ present   · absent )')
    print(divider)
    print(hdr)
    print(divider)

    rows = []
    for combo in product([True, False], repeat=4):
        mask = pd.Series(True, index=df.index)
        for col, val in zip(SECTION_COLS, combo):
            mask &= df[col] == val
        count   = int(mask.sum())
        symbols = ['✓' if v else '·' for v in combo]
        rows.append((count, symbols))

    # Non-zero rows descending by count, then zero rows
    rows.sort(key=lambda r: -r[0])
    for count, symbols in rows:
        sym_str = ''.join(f'{s:<{col_w}}' for s in symbols)
        empty   = '  (empty)' if count == 0 else ''
        print(f'  {sym_str}{count:>7}  {count / total * 100:>6.1f} %{empty}')


def print_report(
    df: pd.DataFrame,
    errors: pd.DataFrame,
    path_col: str,
    language: str,
    venv_df: pd.DataFrame | None = None,
) -> None:
    """Print a human-readable analysis report to stdout.

    Parameters
    ----------
    df : pd.DataFrame
        Project docstrings (venv already excluded for Python).
    errors : pd.DataFrame
        Error rows produced by :func:`find_errors`.
    path_col : str
        Column name that identifies each code element (``'route'`` for
        Python, ``'path'`` for TypeScript).
    language : str
        Display name used in the report header.
    venv_df : pd.DataFrame or None, optional
        Rows that were removed as venv files.  When provided the report
        shows a ``raw_total`` line above the ``correct_total``.
    """
    n_venv     = len(venv_df) if venv_df is not None else 0
    raw_total  = len(df) + n_venv
    total      = len(df)           # correct_total
    n_errors   = len(errors)
    n_valid    = total - n_errors
    error_rate = n_errors / total * 100 if total else 0.0

    print(f'\n{_sep()}')
    print(f'  {language} Docstring Analysis')
    print(_sep())

    if venv_df is not None:
        print(f'  {"Raw total (incl. .venv)":<32} {raw_total:>6}')
        print(f'  {"  └─ excluded (.venv files)":<32} {n_venv:>6}')
        print(f'  {"─" * 40}')

    print(f'  {"Correct total (project files)":<32} {total:>6}')
    print(f'  {"  ├─ valid docstrings":<32} {n_valid:>6}')
    print(f'  {"  └─ errors":<32} {n_errors:>6}  ({error_rate:.1f} %)')

    # ── Error breakdown ────────────────────────────────────────────────────
    if n_errors:
        print(f'\n  Error breakdown:')
        for etype, count in errors['error_type'].value_counts().items():
            pct = count / total * 100
            print(f'    {etype:<28} {count:>4}  ({pct:.1f} %)')
        print(f'\n  Error locations:')
        for _, row in errors.iterrows():
            print(f'    [{row["error_type"]}]  {row[path_col]}')
    else:
        print('\n  ✓ No errors detected.')

    # ── Length statistics ──────────────────────────────────────────────────
    print(f'\n  Docstring length statistics (characters):')
    for stat, val in compute_length_stats(df).items():
        print(f'    {stat:<12} {val:>10.1f}')

    # ── Line-count quartiles ───────────────────────────────────────────────
    df_q = compute_line_quartiles(df)
    if df_q['quartile'].notna().any():
        print(f'\n  Docstring count per line-count quartile:')
        for q, grp in df_q.groupby('quartile', observed=True):
            lo, hi = int(grp['line_count'].min()), int(grp['line_count'].max())
            print(f'    {q}  ({lo}–{hi} lines)  →  {len(grp):>4} docstrings')

    # ── Section analysis ───────────────────────────────────────────────────
    _print_section_analysis(df, language)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare_results(
    py_df:     pd.DataFrame,
    py_errors: pd.DataFrame,
    ts_df:     pd.DataFrame,
    ts_errors: pd.DataFrame,
) -> None:
    """Print a side-by-side comparison summary for Python vs TypeScript.

    Parameters
    ----------
    py_df : pd.DataFrame
        Project-only Python docstring DataFrame (venv excluded).
    py_errors : pd.DataFrame
        Python error rows.
    ts_df : pd.DataFrame
        Full TypeScript docstring DataFrame.
    ts_errors : pd.DataFrame
        TypeScript error rows.
    """
    py_rate   = len(py_errors) / len(py_df) * 100 if py_df is not None and len(py_df) else 0.0
    ts_rate   = len(ts_errors) / len(ts_df) * 100 if ts_df is not None and len(ts_df) else 0.0
    py_avg    = py_df['docstring'].dropna().str.len().mean()
    ts_avg    = ts_df['docstring'].dropna().str.len().mean()
    py_median = py_df['docstring'].dropna().str.len().median()
    ts_median = ts_df['docstring'].dropna().str.len().median()

    # Section presence rates for comparison
    py_sec = detect_sections(py_df)
    ts_sec = detect_sections(ts_df)

    print(f'\n{_sep()}')
    print('  Comparison Summary  —  Python vs TypeScript')
    print(_sep())
    print(f'  {"Metric":<34} {"Python":>10}  {"TypeScript":>10}')
    print(f'  {"-" * 56}')

    def row(label: str, py_val: str, ts_val: str) -> None:
        print(f'  {label:<34} {py_val:>10}  {ts_val:>10}')

    row('Correct total (project files)',
        str(len(py_df)), str(len(ts_df)))
    row('Valid docstrings',
        str(len(py_df) - len(py_errors)), str(len(ts_df) - len(ts_errors)))
    row('Errors',
        str(len(py_errors)), str(len(ts_errors)))
    row('Error rate',
        f'{py_rate:.1f} %', f'{ts_rate:.1f} %')
    row('Avg docstring length',
        f'{py_avg:.0f} ch', f'{ts_avg:.0f} ch')
    row('Median docstring length',
        f'{py_median:.0f} ch', f'{ts_median:.0f} ch')

    print(f'  {"-" * 56}')
    for col, name in zip(SECTION_COLS, SECTION_NAMES):
        py_n = int(py_sec[col].sum())
        ts_n = int(ts_sec[col].sum())
        py_p = py_n / len(py_df) * 100 if len(py_df) else 0
        ts_p = ts_n / len(ts_df) * 100 if len(ts_df) else 0
        row(f'Has {name}',
            f'{py_n} ({py_p:.0f} %)', f'{ts_n} ({ts_p:.0f} %)')
    print()


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def analyse_python_results() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load python_docstrings.json, filter .venv, detect errors and print report.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        ``(project_df, error_df)`` — both limited to project files.
    """
    raw_df      = load_file('python_docstrings.json')
    df, venv_df = split_venv(raw_df, path_col='route')
    errors      = find_errors(df)
    print_report(df, errors, path_col='route', language='Python', venv_df=venv_df)
    return df, errors


def analyse_typescript_results() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load typescript_docstrings.json, detect errors and print report.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        ``(full_df, error_df)``.
    """
    df     = load_file('typescript_docstrings.json')
    errors = find_errors(df)
    print_report(df, errors, path_col='path', language='TypeScript')
    return df, errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    py_df, py_errors = analyse_python_results()
    ts_df, ts_errors = analyse_typescript_results()
    compare_results(py_df, py_errors, ts_df, ts_errors)