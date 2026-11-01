#!/usr/bin/env python3
"""
pdf_extractor.py — Estrai pagine da un PDF con navigazione interattiva nel filesystem.
Uso: python pdf_extractor.py
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
# SELEZIONE DEL FILE PDF
# ─────────────────────────────────────────────

def select_pdf() -> tuple[Path, int]:
    """
    Chiede all'utente il path del PDF con supporto Tab-completion.
    Ritorna il path validato e il numero di pagine.
    """
    print("\n📂  Inserisci il path del file PDF (Tab per autocompletare, se supportato):\n")

    while True:
        try:
            raw = input("  PDF > ").strip()
        except EOFError:
            # Ctrl+D: l'utente vuole uscire
            print("\nUscita.")
            raise SystemExit(0)

        if not raw:
            print("  ⚠️  Path vuoto. Riprova.")
            continue

        path = Path(os.path.expanduser(raw))

        if not path.exists():
            print(f"  ✗  File non trovato: {path}")
            continue

        if not path.is_file():
            print(f"  ✗  Il path punta a una cartella, non a un file: {path}")
            continue

        if path.suffix.lower() != ".pdf":
            print(f"  ✗  Il file non ha estensione .pdf: {path.name}")
            continue

        # Verifica che il file sia effettivamente leggibile da pypdf
        try:
            reader = PdfReader(str(path))
            total_pages = len(reader.pages)
        except Exception as e:
            print(f"  ✗  Impossibile leggere il PDF: {e}")
            continue

        print(f"\n  ✓  File caricato: {path.name}  ({total_pages} pagine totali)")
        return path, total_pages


# ─────────────────────────────────────────────
# PARSER DELL'INTERVALLO DI PAGINE
# ─────────────────────────────────────────────

def parse_page_selection(raw: str, total_pages: int) -> list[int]:
    """
    Converte una stringa tipo "1,5,10-20,30" in una lista ordinata
    di indici 0-based pronti per pypdf.

    Raises ValueError con un messaggio leggibile se l'input è invalido.
    """
    if not raw.strip():
        raise ValueError("L'input è vuoto.")

    page_numbers = set()  # Usiamo un set per eliminare i duplicati automaticamente

    tokens = raw.split(",")

    for token in tokens:
        token = token.strip()

        if not token:
            raise ValueError(f"Token vuoto trovato (virgola doppia?).")

        if "-" in token:
            # ── Caso intervallo: "10-20" ──
            parts = token.split("-")

            # Gestiamo il caso "1--5" o "1-2-3" (troppi trattini)
            if len(parts) != 2:
                raise ValueError(
                    f"Intervallo non valido: '{token}'. "
                    f"Formato atteso: 'inizio-fine' (es. '10-20')."
                )

            start_str, end_str = parts

            if not start_str.isdigit() or not end_str.isdigit():
                raise ValueError(
                    f"Intervallo '{token}' contiene caratteri non numerici."
                )

            start = int(start_str)
            end = int(end_str)

            if start > end:
                raise ValueError(
                    f"Intervallo invertito: '{token}'. "
                    f"Il numero iniziale deve essere ≤ quello finale."
                )

            if start < 1:
                raise ValueError(
                    f"Pagina {start} non esiste: le pagine iniziano da 1."
                )

            if end > total_pages:
                raise ValueError(
                    f"Pagina {end} non esiste: il PDF ha solo {total_pages} pagine."
                )

            for p in range(start, end + 1):
                page_numbers.add(p)

        else:
            # ── Caso pagina singola: "5" ──
            if not token.isdigit():
                raise ValueError(
                    f"'{token}' non è un numero valido."
                )

            page = int(token)

            if page < 1:
                raise ValueError(
                    f"Pagina {page} non esiste: le pagine iniziano da 1."
                )

            if page > total_pages:
                raise ValueError(
                    f"Pagina {page} non esiste: il PDF ha solo {total_pages} pagine."
                )

            page_numbers.add(page)

    # Ordina e converte da 1-based (utente) a 0-based (pypdf)
    return sorted(p - 1 for p in page_numbers)


def ask_page_selection(total_pages: int) -> list[int]:
    """
    Loop interattivo che chiede l'intervallo di pagine finché l'input è valido.
    Ritorna la lista di indici 0-based.
    """
    print(
        f"\n📄  Inserisci le pagine da estrarre (il PDF ne ha {total_pages}).\n"
        f"    Formati accettati:  5        →  pagina singola\n"
        f"                        10-20    →  intervallo continuo\n"
        f"                        1,5,10-20,30  →  combinazione mista\n"
    )

    while True:
        try:
            raw = input("  Pagine > ").strip()
        except EOFError:
            print("\nUscita.")
            raise SystemExit(0)

        try:
            indices = parse_page_selection(raw, total_pages)
            print(f"\n  ✓  Selezionate {len(indices)} pagine.")
            return indices
        except ValueError as e:
            print(f"  ✗  {e}  Riprova.")


# ─────────────────────────────────────────────
# SCELTA DEL FILE DI OUTPUT
# ─────────────────────────────────────────────

def ask_output_path(source_path: Path) -> Path:
    """
    Chiede all'utente:
      1. La cartella di destinazione (default: ~/Downloads).
      2. Il nome del file di output (default: <stem>_estratto.pdf).

    Supporta Tab-completion per la cartella.
    Ritorna il Path completo del file di output (non ancora creato).
    """
    default_dir = Path.home() / "Downloads"
    default_name = f"{source_path.stem}_estratto.pdf"

    print(f"\n💾  Salvataggio del file estratto.")

    # ── Cartella di destinazione ──
    print(f"    Cartella di destinazione (Invio per usare ~/Downloads, Tab per completare):")
    while True:
        try:
            raw_dir = input("  Cartella > ").strip()
        except EOFError:
            print("\nUscita.")
            raise SystemExit(0)

        if not raw_dir:
            out_dir = default_dir
        else:
            out_dir = Path(os.path.expanduser(raw_dir))

        # Accettiamo sia cartelle esistenti che percorsi che possiamo creare
        if out_dir.exists() and not out_dir.is_dir():
            print(f"  ✗  '{out_dir}' esiste ma non è una cartella. Riprova.")
            continue

        break  # percorso valido (esiste o sarà creato)

    # ── Nome del file ──
    print(f"    Nome del file (Invio per usare '{default_name}'):")
    while True:
        try:
            raw_name = input("  Nome > ").strip()
        except EOFError:
            print("\nUscita.")
            raise SystemExit(0)

        if not raw_name:
            output_name = default_name
        else:
            # Assicuriamo che abbia estensione .pdf
            output_name = raw_name if raw_name.lower().endswith(".pdf") else raw_name + ".pdf"

        # Il nome non deve contenere separatori di path
        if os.sep in output_name or (os.altsep and os.altsep in output_name):
            print(f"  ✗  Il nome non deve contenere separatori di percorso. Riprova.")
            continue

        break

    # Crea la cartella se non esiste
    out_dir.mkdir(parents=True, exist_ok=True)

    output_path = out_dir / output_name

    # Se il file esiste già, chiede conferma di sovrascrittura
    if output_path.exists():
        print(f"  ⚠️  Il file '{output_name}' esiste già in '{out_dir}'.")
        while True:
            try:
                confirm = input("  Sovrascrivere? [s/N] > ").strip().lower()
            except EOFError:
                print("\nUscita.")
                raise SystemExit(0)
            if confirm in ("s", "si", "sì", "y", "yes"):
                break
            elif confirm in ("", "n", "no"):
                # Ricomincia chiedendo solo il nome
                return ask_output_path(source_path)
            else:
                print("  ✗  Risposta non valida. Digita 's' per sovrascrivere o 'n' per cambiare nome.")

    print(f"\n  ✓  Il file sarà salvato come: {output_path}")
    return output_path


# ─────────────────────────────────────────────
# ESTRAZIONE E SALVATAGGIO
# ─────────────────────────────────────────────

def extract_and_save(source_path: Path, indices: list[int], output_path: Path) -> Path:
    """
    Estrae le pagine indicate da source_path e salva il risultato
    in output_path.

    Ritorna il Path del file creato.
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

    # Fase 1 — Selezione del file
    source_path, total_pages = select_pdf()

    # Fase 2 — Selezione delle pagine
    indices = ask_page_selection(total_pages)

    # Fase 3 — Scelta del file di output
    output_path = ask_output_path(source_path)

    # Fase 4 — Estrazione e salvataggio
    print("\n⏳  Estrazione in corso...")
    output_path = extract_and_save(source_path, indices, output_path)

    print(f"\n✅  PDF salvato in:\n    {output_path}\n")


if __name__ == "__main__":
    main()
