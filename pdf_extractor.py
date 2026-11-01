#!/usr/bin/env python3
"""Extract selected pages from a PDF with interactive filesystem navigation.

Run with: python pdf_extractor.py
"""

import os
import glob
from pathlib import Path
# pyrefly: ignore [missing-import]
from pypdf import PdfReader, PdfWriter


# ─────────────────────────────────────────────
# TAB-COMPLETION
# ─────────────────────────────────────────────

def path_completer(text, state):
    """
    Callback per readline. Viene chiamata con (text, state) ogni volta che
    l'utente preme Tab. Restituisce il completamento numero `state`, o None
    quando le opzioni sono finite.
    """
    # Se l'utente ha scritto qualcosa, cerchiamo tutto ciò che inizia con quel testo.
    # Il carattere ~ viene espanso manualmente perché glob non lo gestisce da solo.
    expanded = os.path.expanduser(text)
    matches = glob.glob(expanded + "*")

    # Alle cartelle aggiungiamo "/" in coda così l'utente capisce subito
    # che può continuare a navigare senza premere Tab di nuovo.
    results = []
    for m in matches:
        if os.path.isdir(m):
            results.append(m + "/")
        else:
            results.append(m)

    # readline chiama questa funzione più volte aumentando `state` di 1 ogni volta.
    # Dobbiamo restituire results[state], oppure None se state è fuori range.
    if state < len(results):
        return results[state]
    return None


def setup_readline():
    """Configura readline con il nostro completer e i delimitatori corretti."""
    try:
        import readline
    except ImportError:
        return

    readline.set_completer(path_completer)

    # I "delimitatori" sono i caratteri che readline usa per capire dove inizia
    # il token da completare. Di default include "/" e "~", che NON vogliamo:
    # senza questa riga, scrivendo "/home/luca/Doc" readline passerebbe solo
    # "Doc" al completer invece del path completo.
    readline.set_completer_delims(" \t\n")

    # Associa Tab al meccanismo di completamento (necessario su alcuni sistemi).
    readline.parse_and_bind("tab: complete")


# ─────────────────────────────────────────────
# PDF FILE SELECTION
# ─────────────────────────────────────────────

def select_pdf() -> tuple[Path, int]:
    """
    Prompt for a PDF path with Tab completion.
    Return the validated path and page count.
    """
    print("\n📂  Enter the path to a PDF file (Tab to complete, if supported):\n")

    while True:
        try:
            raw = input("  PDF > ").strip()
        except EOFError:
            # Ctrl+D: l'utente vuole uscire
            print("\nGoodbye.")
            raise SystemExit(0)

        if not raw:
            print("  ⚠️  Empty path. Try again.")
            continue

        path = Path(os.path.expanduser(raw))

        if not path.exists():
            print(f"  ✗  File not found: {path}")
            continue

        if not path.is_file():
            print(f"  ✗  Path points to a directory, not a file: {path}")
            continue

        if path.suffix.lower() != ".pdf":
            print(f"  ✗  File does not have a .pdf extension: {path.name}")
            continue

        # Verifica che il file sia effettivamente leggibile da pypdf
        try:
            reader = PdfReader(str(path))
            total_pages = len(reader.pages)
        except Exception as e:
            print(f"  ✗  Could not read the PDF: {e}")
            continue

        print(f"\n  ✓  Loaded: {path.name}  ({total_pages} pages)")
        return path, total_pages


# ─────────────────────────────────────────────
# PAGE SELECTION PARSER
# ─────────────────────────────────────────────

def parse_page_selection(raw: str, total_pages: int) -> list[int]:
    """
    Convert a string like "1,5,10-20,30" into a sorted list
    of zero-based indices for pypdf.

    Raise ValueError with a readable message if the input is invalid.
    """
    if not raw.strip():
        raise ValueError("Input is empty.")

    page_numbers = set()  # Use a set to automatically remove duplicates.

    tokens = raw.split(",")

    for token in tokens:
        token = token.strip()

        if not token:
            raise ValueError("Empty item found (possibly a double comma).")

        if "-" in token:
            # ── Range case: "10-20" ──
            parts = token.split("-")

            # Handle cases like "1--5" or "1-2-3" (too many hyphens).
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid range: '{token}'. "
                    f"Expected format: 'start-end' (for example, '10-20')."
                )

            start_str, end_str = parts

            if not start_str.isdigit() or not end_str.isdigit():
                raise ValueError(
                    f"Range '{token}' contains non-numeric characters."
                )

            start = int(start_str)
            end = int(end_str)

            if start > end:
                raise ValueError(
                    f"Reversed range: '{token}'. "
                    f"The starting page must be less than or equal to the ending page."
                )

            if start < 1:
                raise ValueError(
                    f"Page {start} does not exist: page numbers start at 1."
                )

            if end > total_pages:
                raise ValueError(
                    f"Page {end} does not exist: the PDF has only {total_pages} pages."
                )

            for p in range(start, end + 1):
                page_numbers.add(p)

        else:
            # ── Single-page case: "5" ──
            if not token.isdigit():
                raise ValueError(
                    f"'{token}' is not a valid number."
                )

            page = int(token)

            if page < 1:
                raise ValueError(
                    f"Page {page} does not exist: page numbers start at 1."
                )

            if page > total_pages:
                raise ValueError(
                    f"Page {page} does not exist: the PDF has only {total_pages} pages."
                )

            page_numbers.add(page)

    # Sort and convert from 1-based (user) to 0-based (pypdf).
    return sorted(p - 1 for p in page_numbers)


def ask_page_selection(total_pages: int) -> list[int]:
    """
    Prompt for a page selection until the input is valid.
    Return the list of zero-based indices.
    """
    print(
        f"\n📄  Enter the pages to extract (the PDF has {total_pages} pages).\n"
        f"    Formats:  5             →  single page\n"
        f"              10-20         →  page range\n"
        f"              1,5,10-20,30  →  combination\n"
    )

    while True:
        try:
            raw = input("  Pagine > ").strip()
        except EOFError:
            print("\nGoodbye.")
            raise SystemExit(0)

        try:
            indices = parse_page_selection(raw, total_pages)
            print(f"\n  ✓  Selected {len(indices)} pages.")
            return indices
        except ValueError as e:
            print(f"  ✗  {e}  Try again.")


# ─────────────────────────────────────────────
# OUTPUT FILE SELECTION
# ─────────────────────────────────────────────

def ask_output_path(source_path: Path) -> Path:
    """
    Prompt for:
      1. The destination folder (default: ~/Downloads).
      2. The output filename (default: <stem>_extracted.pdf).

    Support Tab completion for the folder.
    Return the full output path (not yet created).
    """
    default_dir = Path.home() / "Downloads"
    default_name = f"{source_path.stem}_extracted.pdf"

    print("\n💾  Save the extracted file.")

    # ── Destination folder ──
    print("    Destination folder (press Enter for ~/Downloads, Tab to complete):")
    while True:
        try:
            raw_dir = input("  Folder > ").strip()
        except EOFError:
            print("\nGoodbye.")
            raise SystemExit(0)

        if not raw_dir:
            out_dir = default_dir
        else:
            out_dir = Path(os.path.expanduser(raw_dir))

        # Accept existing directories and paths that can be created.
        if out_dir.exists() and not out_dir.is_dir():
            print(f"  ✗  '{out_dir}' exists but is not a directory. Try again.")
            continue

        break  # The path is valid (it exists or can be created).

    # ── Filename ──
    print(f"    Filename (press Enter for '{default_name}'):")
    while True:
        try:
            raw_name = input("  Nome > ").strip()
        except EOFError:
            print("\nGoodbye.")
            raise SystemExit(0)

        if not raw_name:
            output_name = default_name
        else:
            # Ensure it has a .pdf extension.
            output_name = raw_name if raw_name.lower().endswith(".pdf") else raw_name + ".pdf"

        # The filename must not contain path separators.
        if os.sep in output_name or (os.altsep and os.altsep in output_name):
            print("  ✗  Filename must not contain path separators. Try again.")
            continue

        break

    # Create the folder if it does not exist.
    out_dir.mkdir(parents=True, exist_ok=True)

    output_path = out_dir / output_name

    # Ask for confirmation before overwriting an existing file.
    if output_path.exists():
        print(f"  ⚠️  '{output_name}' already exists in '{out_dir}'.")
        while True:
            try:
                confirm = input("  Overwrite? [y/N] > ").strip().lower()
            except EOFError:
                print("\nGoodbye.")
                raise SystemExit(0)
            if confirm in ("y", "yes", "s", "si", "sì"):
                break
            elif confirm in ("", "n", "no"):
                # Restart and ask for the filename again.
                return ask_output_path(source_path)
            else:
                print("  ✗  Invalid response. Enter 'y' to overwrite or 'n' to choose another name.")

    print(f"\n  ✓  The file will be saved as: {output_path}")
    return output_path


# ─────────────────────────────────────────────
# EXTRACTION AND SAVING
# ─────────────────────────────────────────────

def extract_and_save(source_path: Path, indices: list[int], output_path: Path) -> Path:
    """
    Extract the selected pages from source_path and save them to output_path.

    Return the path of the created file.
    """
    reader = PdfReader(str(source_path))
    writer = PdfWriter()

    for i in indices:
        writer.add_page(reader.pages[i])

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("╔══════════════════════════════════════╗")
    print("║        PDF Page Extractor            ║")
    print("╚══════════════════════════════════════╝")

    setup_readline()

    # Step 1 — Select the source file
    source_path, total_pages = select_pdf()

    # Step 2 — Select pages
    indices = ask_page_selection(total_pages)

    # Step 3 — Choose the output file
    output_path = ask_output_path(source_path)

    # Step 4 — Extract and save
    print("\n⏳  Extracting pages...")
    output_path = extract_and_save(source_path, indices, output_path)

    print(f"\n✅  PDF saved to:\n    {output_path}\n")


if __name__ == "__main__":
    main()
