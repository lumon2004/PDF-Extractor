# PDF Page Extractor

A small, interactive command-line tool for extracting selected pages from a PDF
into a new PDF file. Files are read and written locally; the tool does not
upload documents.

## Features

- Select a PDF by entering its path, with Tab completion where the platform
  provides Python's `readline` module.
- Extract individual pages, ranges, or a combination of both.
- Choose the output folder and filename; confirm before overwriting an
  existing file.

## Requirements

- Python 3.9 or later
- A PDF readable by [pypdf](https://pypi.org/project/pypdf/)

## Install

### From PyPI

Once the package is published:

```bash
python -m pip install pdf-page-extractor
```

### From the GitHub repository

After the repository is public:

```bash
python -m pip install git+https://github.com/lumon2004/PDF-Extractor.git
```

Alternatively, clone the repository and install it locally:

```bash
git clone https://github.com/lumon2004/PDF-Extractor.git
cd PDF-Extractor
python -m venv .venv
```

Activate the virtual environment, then install:

```bash
# macOS / Linux
source .venv/bin/activate
python -m pip install .
```

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

## Run

```bash
pdf-extractor
```

The program prompts for the source PDF, the pages to extract, and the output
location. For example, enter `1,5,10-12` to select pages 1, 5, 10, 11, and 12.
Page numbers start at 1; duplicate selections are removed and pages are saved
in ascending order.

Press Enter at the output-folder prompt to use `~/Downloads`. If that folder
does not exist, it is created. On systems without `readline` (including a
standard Windows Python installation), path entry still works but Tab
completion is unavailable.

## Development

Install the project and its runtime dependency in an isolated environment as
shown above. To run the script directly from a checkout:

```bash
python pdf_extractor.py
```

## License

Distributed under the Apache License 2.0. See [LICENSE](LICENSE).
