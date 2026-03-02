"""Streamlit UI for the Flashcard Factory."""

from __future__ import annotations

import logging
import random as _rng
import re
import threading
import time
from pathlib import Path

import streamlit as st

from pipeline import (
    CardSize,
    Operation,
    PipelineCancelled,
    PipelineConfig,
    Style,
    run_pipeline,
)

logging.basicConfig(level=logging.INFO)

BASE_PATH = Path(__file__).resolve().parent
ASSETS_ROOT = BASE_PATH / "input" / "Assets"
ASSETS_ROOT.mkdir(parents=True, exist_ok=True)

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Flashcard Factory | Printable Math Flashcards",
    page_icon="✏️",
    layout="centered",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

st.markdown("""<style>
/* ── Typography ── */
.stApp {
    font-family: 'Nunito', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
/* These elements don't inherit font in CSS, so set explicitly */
.stApp button, .stApp input, .stApp select, .stApp textarea {
    font-family: inherit !important;
}
.block-container { max-width: 800px; padding-top: 1.5rem; }

/* ── Step headers ── */
.step-header {
    display: flex; align-items: center; gap: 0.6rem;
    margin-top: 1.6rem; margin-bottom: 0.1rem;
}
.step-num {
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 50%;
    background: #5B8A9A; color: white;
    font-weight: 800; font-size: 0.85rem; flex-shrink: 0;
}
.step-label { font-size: 1.15rem; font-weight: 800; color: #2D3748; }
.step-desc {
    color: #718096; font-size: 0.88rem;
    margin-bottom: 0.7rem; padding-left: 2.4rem;
}

/* ── Difficulty pills ── */
.pill-row { display: inline-flex; gap: 0.35rem; margin-top: 0.25rem; }
.pill {
    padding: 2px 10px; border-radius: 20px;
    font-size: 0.76rem; font-weight: 700;
}
.pill-easy   { background: #DBEAFE; color: #1E40AF; }
.pill-medium { background: #D1FAE5; color: #065F46; }
.pill-hard   { background: #FEE2E2; color: #991B1B; }

/* ── Stat boxes ── */
.stat-row { display: flex; gap: 1rem; margin: 1rem 0; }
.stat-box {
    flex: 1; text-align: center;
    background: #F0F7FA; border: 1px solid #D5E3EA;
    border-radius: 12px; padding: 0.9rem 0.5rem;
}
.stat-box .num {
    font-size: 1.8rem; font-weight: 800;
    color: #2D3748; line-height: 1.2;
}
.stat-box .label {
    font-size: 0.78rem; color: #718096;
    text-transform: uppercase; letter-spacing: 0.5px;
}

/* ── Download cards ── */
.dl-card {
    background: #F0F7FA; border: 1px solid #D5E3EA;
    border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
}
.dl-card h4 { margin: 0 0 0.5rem 0; font-size: 1rem; color: #2D3748; }

/* ── Divider ── */
.divider { border: none; border-top: 1px solid #E2E8F0; margin: 1.5rem 0; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
</style>""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────

st.markdown("# ✏️ Flashcard Factory")
st.markdown(
    "Create **beautiful, print-ready math flashcards** for your classroom or "
    "home. Pick your images, choose an operation, customise the look, and "
    "generate double-sided A4 PDFs in seconds."
)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Discover asset packs ─────────────────────────────────────────────────────


def _discover_packs() -> list[str]:
    return sorted(
        d.name
        for d in ASSETS_ROOT.iterdir()
        if d.is_dir() and any(d.glob("*.png"))
    )


packs = _discover_packs()

# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 - Choose Your Images
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    '<div class="step-header">'
    '<span class="step-num">1</span>'
    '<span class="step-label">Choose Your Images</span>'
    "</div>"
    '<p class="step-desc">'
    "Select an image pack. Each flashcard will feature pictures from it."
    "</p>",
    unsafe_allow_html=True,
)

if packs:
    asset_pack = st.selectbox(
        "Image pack",
        packs,
        index=0,
        label_visibility="collapsed",
    )

    # Show thumbnail preview of the selected pack
    pack_dir = ASSETS_ROOT / asset_pack
    sample_imgs = sorted(pack_dir.glob("*.png"))[:8]
    if sample_imgs:
        cols = st.columns(len(sample_imgs))
        for i, p in enumerate(sample_imgs):
            with cols[i]:
                st.image(str(p), caption=p.stem, use_container_width=True)
        total_in_pack = len(list(pack_dir.glob("*.png")))
        if total_in_pack > 8:
            st.caption(f"…and {total_in_pack - 8} more images in this pack")
else:
    st.info("No image packs found yet. Create one below to get started!")
    asset_pack = None

# Custom pack upload
with st.expander("Create your own image pack"):
    st.markdown(
        "Upload **PNG images** (square with transparent backgrounds work best). "
        "The file name becomes the label on each card. For example, "
        "`Cat.png` produces *\"How many Cats are there now?\"*"
    )

    new_pack_name = st.text_input(
        "Pack name",
        placeholder="e.g. Dinosaurs, Fruits, Vehicles…",
        key="new_pack_name",
    )

    uploaded = st.file_uploader(
        "Upload images",
        type=["png"],
        accept_multiple_files=True,
        key="pack_upload",
    )

    if uploaded:
        st.caption(f"{len(uploaded)} image(s) selected")
        preview_cols = st.columns(min(len(uploaded), 6))
        for i, f in enumerate(uploaded[:6]):
            with preview_cols[i]:
                st.image(f, caption=Path(f.name).stem, use_container_width=True)
        if len(uploaded) > 6:
            st.caption(f"…and {len(uploaded) - 6} more")

    can_save_pack = bool(new_pack_name and new_pack_name.strip() and uploaded)
    if st.button("Save pack", disabled=not can_save_pack, type="primary"):
        clean = re.sub(r"[^\w\s-]", "", new_pack_name).strip().title()
        if not clean:
            st.error("Please enter a valid pack name (letters, numbers, spaces).")
        else:
            dest = ASSETS_ROOT / clean
            dest.mkdir(parents=True, exist_ok=True)
            for f in uploaded:
                (dest / f.name).write_bytes(f.getvalue())
            st.success(
                f"Saved **{clean}** with {len(uploaded)} images! "
                "It will appear in the dropdown above."
            )
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 - Pick the Operation
# ═════════════════════════════════════════════════════════════════════════════

st.markdown('<hr class="divider">', unsafe_allow_html=True)

st.markdown(
    '<div class="step-header">'
    '<span class="step-num">2</span>'
    '<span class="step-label">Pick the Math Operation</span>'
    "</div>"
    '<p class="step-desc">'
    "Every card will show a problem using the operation you choose."
    "</p>",
    unsafe_allow_html=True,
)

operation = st.radio(
    "Operation",
    [Operation.ADDITION.value, Operation.SUBTRACTION.value],
    horizontal=True,
    label_visibility="collapsed",
    captions=[
        "e.g.  3 + 4 = 7",
        "e.g.  9 − 3 = 6",
    ],
)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 3 - Card Style
# ═════════════════════════════════════════════════════════════════════════════

st.markdown('<hr class="divider">', unsafe_allow_html=True)

st.markdown(
    '<div class="step-header">'
    '<span class="step-num">3</span>'
    '<span class="step-label">Choose a Style</span>'
    "</div>"
    '<p class="step-desc">'
    "You can generate one or both styles at the same time."
    "</p>",
    unsafe_allow_html=True,
)

col_std, col_cg = st.columns(2)

with col_std:
    use_standard = st.checkbox("Standard", value=True)
    st.caption("Clean navy-blue design on every card.")

with col_cg:
    use_color = st.checkbox("Color-Coded by Difficulty", value=True)
    if use_color:
        st.caption("Sorted by difficulty:")
        st.markdown(
            '<div class="pill-row">'
            '<span class="pill pill-easy">Easy</span>'
            '<span class="pill pill-medium">Medium</span>'
            '<span class="pill pill-hard">Hard</span>'
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption("Cards tinted by difficulty so learners can self-sort.")

# ═════════════════════════════════════════════════════════════════════════════
# STEP 4 - Card Sizes
# ═════════════════════════════════════════════════════════════════════════════

st.markdown('<hr class="divider">', unsafe_allow_html=True)

st.markdown(
    '<div class="step-header">'
    '<span class="step-num">4</span>'
    '<span class="step-label">Choose Card Sizes</span>'
    "</div>"
    '<p class="step-desc">'
    "Pick one or more. Each generates a separate print-ready PDF."
    "</p>",
    unsafe_allow_html=True,
)

col_lg, col_md, col_sm = st.columns(3)

with col_lg:
    use_large = st.checkbox("Large (2 per page)")
    st.caption("Big and bold. Great for little hands.")

with col_md:
    use_medium = st.checkbox("Medium (4 per page)", value=True)
    st.caption("A good balance of size and paper use.")

with col_sm:
    use_small = st.checkbox("Small (5 per page)", value=True)
    st.caption("Compact and paper-friendly.")

# ── Advanced options ─────────────────────────────────────────────────────────

with st.expander("Advanced options"):
    st.markdown(
        "The **seed** controls how images are shuffled and assigned to cards. "
        "The same seed always produces the same set of flashcards."
    )
    st.caption(
        "Write this number down if you want to reproduce the exact same "
        "flashcards later."
    )

    if "seed_input" not in st.session_state:
        st.session_state["seed_input"] = "234"

    # Randomize must run BEFORE the text_input widget is created,
    # otherwise Streamlit won't allow modifying its session key.
    _do_randomize = st.session_state.pop("_do_randomize", False)
    if _do_randomize:
        st.session_state["seed_input"] = str(_rng.randint(1, 99999))

    seed_col, apply_col, rand_col = st.columns([3, 1, 1])
    with seed_col:
        seed_text = st.text_input(
            "Seed",
            key="seed_input",
            label_visibility="collapsed",
        )
    with apply_col:
        st.button("Apply", use_container_width=True)
    with rand_col:
        if st.button("🎲 Randomize", use_container_width=True):
            st.session_state["_do_randomize"] = True
            st.rerun()

    try:
        random_seed = int(seed_text)
        st.markdown(
            f'<p style="font-size:0.82rem; color:#5B8A9A; margin-top:-0.5rem;">'
            f'Current seed: <b>{random_seed}</b></p>',
            unsafe_allow_html=True,
        )
    except ValueError:
        random_seed = 234
        st.warning("Seed must be a whole number.")

# ── Validation ───────────────────────────────────────────────────────────────

styles: list[Style] = []
if use_standard:
    styles.append(Style.STANDARD)
if use_color:
    styles.append(Style.COLOR_GRADED)

sizes: list[CardSize] = []
if use_large:
    sizes.append(CardSize.LARGE)
if use_medium:
    sizes.append(CardSize.MEDIUM)
if use_small:
    sizes.append(CardSize.SMALL)

can_generate = bool(styles) and bool(sizes) and asset_pack is not None

if not styles:
    st.warning("Select at least one card style above.")
elif not sizes:
    st.warning("Select at least one card size above.")
elif asset_pack is None:
    st.warning("Create an image pack first (step 1) before generating.")

# ═════════════════════════════════════════════════════════════════════════════
# Generate (with background thread + cancel support)
# ═════════════════════════════════════════════════════════════════════════════

st.markdown('<hr class="divider">', unsafe_allow_html=True)


def _run_pipeline_thread(gen_state: dict) -> None:
    """Target for the background thread — runs the pipeline and stores results."""
    config: PipelineConfig = gen_state["config"]
    total_stages: int = gen_state["total_stages"]
    done = [0]

    def _on_stage(msg: str) -> None:
        done[0] += 1
        gen_state["progress"] = min(done[0] / total_stages, 1.0)
        gen_state["progress_text"] = msg

    def _on_card(current: int, total: int, label: str) -> None:
        frac = (done[0] - 1 + current / total) / total_stages
        gen_state["progress"] = min(frac, 1.0)
        gen_state["progress_text"] = f"Creating {label} cards: {current} / {total}"

    def _on_pdf(msg: str) -> None:
        gen_state["progress_text"] = msg

    try:
        result = run_pipeline(
            config,
            on_stage=_on_stage,
            on_card_progress=_on_card,
            on_pdf_progress=_on_pdf,
            cancelled=gen_state["cancel_event"].is_set,
        )
        gen_state["result"] = result
    except PipelineCancelled:
        gen_state["cancelled"] = True
    except Exception as exc:
        gen_state["error"] = str(exc)
    finally:
        gen_state["done"] = True


# Initialize gen_state in session_state if absent
if "gen_state" not in st.session_state:
    st.session_state["gen_state"] = None

gen_state = st.session_state["gen_state"]

if gen_state is not None and not gen_state["done"]:
    # ── Currently generating — show progress + cancel button ──
    st.markdown("**Generating flashcards…**")
    progress_bar = st.progress(gen_state.get("progress", 0.0))
    st.markdown(gen_state.get("progress_text", "Starting…"))

    if st.button("Cancel Generation", type="secondary", use_container_width=True):
        gen_state["cancel_event"].set()

    time.sleep(0.3)
    st.rerun()

elif gen_state is not None and gen_state["done"]:
    # ── Generation finished — process results ──
    if gen_state.get("cancelled"):
        st.warning("Generation cancelled. Partial files have been cleaned up.")
        st.session_state["gen_state"] = None
        # Clear any stale results
        st.session_state.pop("result_pdfs", None)
        st.session_state.pop("result_config", None)
        st.session_state.pop("card_count", None)

    elif gen_state.get("error"):
        st.error(f"Pipeline error: {gen_state['error']}")
        st.session_state["gen_state"] = None

    elif gen_state.get("result"):
        config_done: PipelineConfig = gen_state["config"]
        result = gen_state["result"]

        st.session_state["result_pdfs"] = result["pdfs"]
        st.session_state["result_config"] = config_done

        cards_dir = config_done.gen_dir(config_done.styles[0])
        card_count = len(list(cards_dir.glob("Card_*[!_Back].png")))
        st.session_state["card_count"] = card_count

        st.session_state["gen_state"] = None
        st.rerun()

    else:
        st.session_state["gen_state"] = None

    # Show generate button again
    if st.button(
        "Generate Flashcards",
        type="primary",
        disabled=not can_generate,
        use_container_width=True,
    ):
        pass  # handled below in the idle branch on next rerun

else:
    # ── Idle — show generate button ──
    if st.button(
        "Generate Flashcards",
        type="primary",
        disabled=not can_generate,
        use_container_width=True,
    ):
        config = PipelineConfig(
            base_path=BASE_PATH,
            asset_pack=asset_pack,
            operation=Operation(operation),
            styles=styles,
            sizes=sizes,
            random_seed=random_seed,
        )

        total_stages = 1 + len(styles) + len(styles) * len(sizes)

        gen_state = {
            "cancel_event": threading.Event(),
            "config": config,
            "total_stages": total_stages,
            "progress": 0.0,
            "progress_text": "Starting…",
            "done": False,
            "result": None,
            "error": None,
            "cancelled": False,
        }
        st.session_state["gen_state"] = gen_state

        thread = threading.Thread(target=_run_pipeline_thread, args=(gen_state,), daemon=True)
        thread.start()

        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# Results (persists across reruns via session_state)
# ═════════════════════════════════════════════════════════════════════════════

if "result_pdfs" in st.session_state:
    pdfs: list[Path] = st.session_state["result_pdfs"]
    config_r: PipelineConfig = st.session_state["result_config"]
    card_count: int = st.session_state.get("card_count", 0)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Stats
    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-box">
                <div class="num">{card_count}</div>
                <div class="label">Cards</div>
            </div>
            <div class="stat-box">
                <div class="num">{len(config_r.styles)}</div>
                <div class="label">Styles</div>
            </div>
            <div class="stat-box">
                <div class="num">{len(pdfs)}</div>
                <div class="label">PDFs</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Tabs
    preview_tab, download_tab = st.tabs(["Preview", "Download"])

    with preview_tab:
        first_style = config_r.styles[0]
        cards_dir = config_r.gen_dir(first_style)
        front_files = sorted(cards_dir.glob("Card_*[!_Back].png"))[:6]

        if front_files:
            st.markdown(
                f"Showing the first {len(front_files)} cards "
                f"({first_style.value} style)"
            )
            cols = st.columns(3)
            for idx, fp in enumerate(front_files):
                bp = fp.with_name(fp.stem + "_Back.png")
                with cols[idx % 3]:
                    st.image(
                        str(fp),
                        caption=f"Card {idx + 1} / Front",
                        use_container_width=True,
                    )
                    if bp.exists():
                        st.image(
                            str(bp),
                            caption=f"Card {idx + 1} / Back",
                            use_container_width=True,
                        )
        else:
            st.info("No preview images found.")

    with download_tab:
        for style in config_r.styles:
            st.markdown(
                f'<div class="dl-card"><h4>{style.value}</h4>',
                unsafe_allow_html=True,
            )
            dl_cols = st.columns(len(config_r.sizes))
            for i, size in enumerate(config_r.sizes):
                pdf_path = config_r.pdf_dir(style) / f"A4_{size.value}.pdf"
                with dl_cols[i]:
                    if pdf_path.exists():
                        st.download_button(
                            label=f"📥 {size.value}",
                            data=pdf_path.read_bytes(),
                            file_name=(
                                f"{config_r.asset_pack}_{config_r.operation.value}"
                                f"_{style.value}_{size.value}.pdf"
                            ),
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    else:
                        st.warning(f"{size.value} PDF not found")
            st.markdown("</div>", unsafe_allow_html=True)

# ── Footer tip ───────────────────────────────────────────────────────────────

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.caption(
    "💡 **Tip:** Print the PDFs **double-sided** on A4 paper, then cut along "
    "the guides for perfectly aligned front-and-back flashcards."
)
