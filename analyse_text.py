#!/usr/bin/env python3
"""
analizar_texto.py

Sends a plain-text file through a local LanguageTool server (Spanish) and
produces a single consolidated Markdown report of spelling, grammar, style
and punctuation issues, grouped by category, with line numbers and
suggested replacements.

Requirements:
    pip install requests

Usage:
    python3 analizar_texto.py midocumento.txt informe.md
    python3 analizar_texto.py midocumento.txt informe.md --lang es-ES --server http://localhost:8010
"""

import argparse
import sys
import time
from collections import defaultdict

try:
    import requests
except ImportError:
    sys.exit("Falta el paquete 'requests'. Instálalo con: pip install requests")

MAX_CHUNK_CHARS = 15000  # keep requests small enough to avoid timeouts


def split_into_chunks(text, max_chars=MAX_CHUNK_CHARS):
    """
    Split text into chunks no larger than max_chars, breaking on paragraph
    boundaries when possible. Returns a list of (chunk_text, start_offset)
    tuples, where start_offset is the character offset of the chunk's
    start within the original text.
    """
    chunks = []
    paragraphs = text.split("\n\n")

    current = []
    current_len = 0
    current_start = 0
    running_offset = 0

    for para in paragraphs:
        para_with_sep = para + "\n\n"
        if current_len + len(para_with_sep) > max_chars and current:
            chunk_text = "".join(current)
            chunks.append((chunk_text, current_start))
            current = []
            current_len = 0
            current_start = running_offset

        current.append(para_with_sep)
        current_len += len(para_with_sep)
        running_offset += len(para_with_sep)

    if current:
        chunk_text = "".join(current)
        chunks.append((chunk_text, current_start))

    return chunks


def load_exceptions(exceptions_file, ignore_arg):
    """Load exception phrases exactly as written (case-sensitive, can be multi-word, e.g. 'et al.')."""
    terms = []
    if exceptions_file:
        with open(exceptions_file, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    terms.append(stripped)
    if ignore_arg:
        for term in ignore_arg.split(","):
            term = term.strip()
            if term:
                terms.append(term)
    return terms


def find_protected_ranges(text, exceptions):
    """Find every occurrence of each exception phrase in text (case-sensitive, exact substring match).
    Returns a list of (start, end) character ranges covered by exceptions."""
    ranges = []
    for phrase in exceptions:
        start = 0
        while True:
            idx = text.find(phrase, start)
            if idx == -1:
                break
            ranges.append((idx, idx + len(phrase)))
            start = idx + 1
    return ranges


def ranges_overlap(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def line_number_at_offset(text, offset):
    """Return the 1-indexed line number containing the given character offset."""
    return text.count("\n", 0, offset) + 1


def check_chunk(server, lang, chunk_text, retries=3):
    url = server.rstrip("/") + "/v2/check"
    data = {"language": lang, "text": chunk_text}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, data=data, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt == retries:
                raise
            print(f"  Aviso: fallo en intento {attempt} ({e}), reintentando...", file=sys.stderr)
            time.sleep(3)


def main():
    parser = argparse.ArgumentParser(
        description="Analiza ortografía, gramática y estilo de un .txt usando LanguageTool local.")
    parser.add_argument("--input_file", default="/home/javi/Documents/TFGSW/TFG/main.txt",
                        help="Ruta al archivo .txt a analizar")
    parser.add_argument("--output_file", default="/home/javi/Documents/TFGSW/TFG/main.analysis.md",
                        help="Ruta al archivo que contiene el análisis.")
    parser.add_argument("--lang", default="es", help="Código de idioma (por defecto: es)")
    parser.add_argument("--server", default="http://localhost:8010", help="URL del servidor LanguageTool")
    parser.add_argument("--exceptions", default='exceptions.txt',
                        help="Archivo con un término por línea a ignorar (ej. Python, UML, back-end)")
    parser.add_argument("--ignore", default=None,
                        help="Términos a ignorar separados por comas (ej. 'Python,UML,back-end,front-end')")
    args = parser.parse_args()

    exceptions = load_exceptions(args.exceptions, args.ignore)
    if exceptions:
        print(f"Ignorando {len(exceptions)} término(s) de la lista de excepciones.")

    with open(args.input_file, "r", encoding="utf-8") as f:
        full_text = f.read()

    chunks = split_into_chunks(full_text)
    print(f"Documento dividido en {len(chunks)} fragmento(s). Analizando con LanguageTool ({args.lang})...")

    all_issues = []  # list of dicts: category, rule_id, message, context, replacements, line

    for i, (chunk_text, chunk_offset) in enumerate(chunks, start=1):
        print(f"  Fragmento {i}/{len(chunks)}...")
        result = check_chunk(args.server, args.lang, chunk_text)
        matches = result.get("matches", [])
        protected_ranges = find_protected_ranges(chunk_text, exceptions)
        for m in matches:
            m_start = m["offset"]
            m_end = m["offset"] + m["length"]
            if any(ranges_overlap(m_start, m_end, p_start, p_end) for p_start, p_end in protected_ranges):
                continue

            global_offset = chunk_offset + m["offset"]
            line_no = line_number_at_offset(full_text, global_offset)
            category = m.get("rule", {}).get("category", {}).get("name", "Otro")
            rule_id = m.get("rule", {}).get("id", "")
            message = m.get("message", "")
            context = m.get("context", {}).get("text", "")
            replacements = [r["value"] for r in m.get("replacements", [])][:5]
            all_issues.append({
                "category": category,
                "rule_id": rule_id,
                "message": message,
                "context": context,
                "replacements": replacements,
                "line": line_no,
            })

    # Group by category
    by_category = defaultdict(list)
    for issue in all_issues:
        by_category[issue["category"]].append(issue)

    # Sort categories by number of issues (descending), then by name
    sorted_categories = sorted(by_category.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    with open(args.output_file, "w", encoding="utf-8") as out:
        out.write(f"# Informe de análisis: {args.input_file}\n\n")
        out.write(f"**Total de incidencias encontradas:** {len(all_issues)}\n\n")

        if all_issues:
            out.write("## Resumen por categoría\n\n")
            for category, issues in sorted_categories:
                out.write(f"- **{category}**: {len(issues)}\n")
            out.write("\n---\n\n")

            for category, issues in sorted_categories:
                out.write(f"## {category} ({len(issues)})\n\n")
                issues_sorted = sorted(issues, key=lambda x: x["line"])
                for issue in issues_sorted:
                    out.write(f"**Línea {issue['line']}** — {issue['message']}\n")
                    out.write(f"    > {issue['context']}\n")
                    if issue["replacements"]:
                        out.write(f"    Sugerencias: {', '.join(issue['replacements'])}\n")
                    out.write(f"    *Regla: `{issue['rule_id']}`*\n\n")
                out.write("---\n\n")
        else:
            out.write("No se encontraron incidencias. ¡Buen trabajo!\n")

    print(f"\nListo. Informe guardado en: {args.output_file}")
    print(f"Total de incidencias: {len(all_issues)}")


if __name__ == "__main__":
    main()