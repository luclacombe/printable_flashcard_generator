"""CLI entry point for the flashcard generation pipeline."""

from __future__ import annotations

import logging
import signal
import threading
from pathlib import Path

from pipeline import CardSize, Operation, PipelineCancelled, PipelineConfig, Style, run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

# ====================================================
#                 MASTER SETTINGS
# ====================================================

ASSET_PACK = "Animals"
OPERATION = Operation.ADDITION
STYLES = [Style.STANDARD, Style.COLOR_GRADED]
SIZES = [CardSize.SMALL, CardSize.MEDIUM]

# ====================================================


def main() -> None:
    print("==========================================")
    print("       FLASHCARD PIPELINE STARTED")
    print("  (Press Ctrl+C to cancel at any time)")
    print("==========================================\n")

    cancel_event = threading.Event()
    original_handler = signal.getsignal(signal.SIGINT)

    def _sigint_handler(signum: int, frame: object) -> None:
        print("\n\nCancelling… (waiting for current step to finish)")
        cancel_event.set()

    signal.signal(signal.SIGINT, _sigint_handler)

    config = PipelineConfig(
        base_path=Path(__file__).resolve().parent,
        asset_pack=ASSET_PACK,
        operation=OPERATION,
        styles=STYLES,
        sizes=SIZES,
    )

    def on_stage(msg: str) -> None:
        print(f"\n** {msg} **")

    def on_card(current: int, total: int, label: str) -> None:
        print(f"  Card {current}/{total} ({label})")

    try:
        result = run_pipeline(
            config,
            on_stage=on_stage,
            on_card_progress=on_card,
            cancelled=cancel_event.is_set,
        )

        print("\n==========================================")
        print("           PIPELINE COMPLETE")
        print("==========================================")
        print(f"\nGenerated {len(result['pdfs'])} PDF(s):")
        for p in result["pdfs"]:
            print(f"  {p}")

    except PipelineCancelled:
        print("\n==========================================")
        print("        PIPELINE CANCELLED")
        print("==========================================")
        print("\nPartial files have been cleaned up.")

    finally:
        signal.signal(signal.SIGINT, original_handler)


if __name__ == "__main__":
    main()
