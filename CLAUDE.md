# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python pipeline that generates print-ready, double-sided A4 PDF math flashcards. It uses image assets (e.g., animals) to create addition/subtraction flashcards with difficulty-based color coding (Easy/Medium/Hard). Pluralization is handled by the `inflect` library. The app has both a Streamlit web UI and a CLI entry point.

## Running the Project

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit web app
streamlit run app.py

# Or run the CLI pipeline directly
python main.py
```

## Architecture

```
FLASHCARDS/
├── app.py                      # Streamlit web UI
├── main.py                     # CLI entry point
├── pipeline/
│   ├── __init__.py             # Public API: run_pipeline()
│   ├── config.py               # Enums, dataclasses, constants
│   ├── operations.py           # Stage 1: math pairs + plurals
│   ├── card_creator.py         # Stage 2: card image compositing
│   ├── pdf_generator.py        # Stage 3: PDF assembly
│   └── pdf_settings.py         # Layout configs per card size
├── input/
│   ├── Assets/{pack}/*.png     # 1000x1000, transparent bg, singular names
│   ├── Assets/Quicksand-Bold.ttf
│   └── templates/*.png         # Card and A4 page templates
└── Gen/                        # Generated output (gitignored)
```

### Pipeline stages (orchestrated by `pipeline/__init__.py`):

1. **`operations.py`** — Generates `FlashCard` dataclass instances with math problems, text, asset assignments, and difficulty. Uses `inflect` for pluralization. Deterministic via `RANDOM_SEED = 234`.

2. **`card_creator.py`** — `CardCreator` class composites front + back card PNGs from templates and asset images. Caches fonts and images for performance.

3. **`pdf_generator.py`** + **`pdf_settings.py`** — Assembles card PNGs into A4 PDFs. Uses `pypdf` for page mirroring (double-sided printing). Layout classes: `LargeLayout` (2/page), `MediumLayout` (4/page), `SmallLayout` (5/page).

## Configuration

- **Streamlit UI**: All settings are configurable via the web interface
- **CLI** (`main.py`): Edit constants at the top of the file
- **Programmatic**: Create a `PipelineConfig` dataclass and call `run_pipeline(config)`

Key config fields: `asset_pack`, `operation` (Addition/Subtraction), `styles` (Standard/Color Graded), `sizes` (Large/Medium/Small)

## Key File Paths

- `input/Assets/{pack}/` — Source PNGs (singular-named like `Cat.png`)
- `input/Assets/Quicksand-Bold.ttf` — Font for all card text
- `input/templates/` — Card templates and A4 page templates
- `Gen/{pack}/Flash Cards/{operation}/` — Generated card PNGs
- `Gen/{pack}/Final_PDFs/{operation}/` — Final print-ready PDFs

## Dependencies

Pillow, reportlab, pypdf, inflect, streamlit.
