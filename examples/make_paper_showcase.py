#!/usr/bin/env python
"""Build the definitive, hand-authored research-paper showcase demo.

Unlike the template-driven ``democreate paper`` generator (which narrates a
paper's literal figure captions), this is a *curated* tour of one real paper —
"Policy Entanglement in Active Inference" — written **show, don't tell**: a
dynamic opening (a hook, the problem, the idea, a λ-sweep that *shows* the knob,
and a stat board) and tight, **interpretive** figure narration — concrete
mechanisms and numbers, not caption-reading, with the framing devices cut.

It is the paper-side analogue of ``examples/make_showcase.py``. The narration is
hand-written (the assistant read the paper's abstract, sections, and all 47
figure captions); the visuals are the paper's own reproducible figures, shown
whole (fit-contain) on the noir canvas, plus a built λ-sweep montage and a
diagram of its codebase.

Render it with::

    democreate render examples/democreate_paper_showcase.json -o output/paper_showcase \
        --voice Daniel --author "Daniel Ari Friedman" \
        --watermark "Policy Entanglement in Active Inference"
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from democreate.schema import Action, ActionType, Chunk, Demo, Scene, SceneKind

# Source inputs are supplied explicitly; output stays beside the Demo JSON.
_REPO = Path(__file__).resolve().parents[1]
_EXAMPLES = _REPO / "examples"
_ASSETS = _EXAMPLES / "assets" / "paper"
_PAPER_ROOT: Path | None = None
_PDF_INPUT = "output/pdf/actinf_policy_entanglement_lean_combined.pdf"
_FIGURE_INPUTS = (
    "pymdp_joint_lambda_0.00.png",
    "pymdp_joint_lambda_2.00.png",
    "pymdp_joint_lambda_4.00.png",
    "joint_heatmap_lambda2.png",
    "ising_mi_curve.png",
    "optimal_lambda.png",
    "coupling_tax_quadratic.png",
    "log_weight_flow.png",
    "archetype_dendrogram.png",
    "multi_k_tt_rank_profile.png",
    "phase_diagram.png",
    "pymdp_coupled_rollout.png",
)


def _source(relative: str) -> Path:
    """Resolve an input, rejecting any escape from the caller's paper root."""
    if _PAPER_ROOT is None:
        raise ValueError("Optional curated showcase requires explicit --paper-root")
    root = _PAPER_ROOT.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"External paper input escapes selected --paper-root: {relative}")
    if not path.exists():
        raise FileNotFoundError(f"Required external paper input missing: {path}")
    if path.is_dir():
        # Validate descendants before the walker can read through a linked parent.
        for child in path.rglob("*"):
            if not child.resolve().is_relative_to(root):
                raise ValueError(
                    f"External paper input escapes selected --paper-root: {child}"
                )
    return path


def _stage(source: Path) -> Path:
    _ASSETS.mkdir(parents=True, exist_ok=True)
    target = _ASSETS / source.name
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    return target


_NOIR_BG = (12, 12, 14)
_NOIR_RED = (224, 49, 57)
_NOIR_FG = (242, 242, 244)


def _slide(id_, section, narration, *, title="", subtitle="", bg=None,
           bullets=None, stats=None) -> Scene:
    scene = Scene(id=id_, title=title or section, kind=SceneKind.SLIDE)
    scene.context["section"] = section
    if subtitle:
        scene.context["subtitle"] = subtitle
    if bg is not None:
        scene.context["background_image"] = bg.relative_to(_EXAMPLES).as_posix()
    if bullets:
        scene.context["bullets"] = bullets
    if stats:
        scene.context["stats"] = stats
    actions = [Action(ActionType.OPEN_FILE, {"path": title or section})] if bg else []
    scene.chunks.append(Chunk(id=f"{id_}-c", text=narration, actions=actions))
    return scene


def _figure(id_, section, fig_file, narration) -> Scene:
    """A figure scene: the paper's real figure, shown whole, with tight
    interpretive narration (the mechanism, not the caption)."""
    fig = _stage(_source(f"output/figures/{fig_file}"))
    return _slide(id_, section, narration, title=section, bg=fig)


def _lambda_sweep() -> Path:
    """Montage the joint posterior at λ = 0, 2, 4 into one frame — *show* the knob.

    Three of the paper's own ``pymdp`` joint-posterior figures laid side by side
    with λ labels, so the independent → entangled transition is visible at a
    glance instead of described in words.
    """
    panels = [
        ("pymdp_joint_lambda_0.00.png", "λ = 0"),
        ("pymdp_joint_lambda_2.00.png", "λ = 2"),
        ("pymdp_joint_lambda_4.00.png", "λ = 4"),
    ]
    from PIL import Image, ImageDraw

    from democreate.animation.fonts import scaled_font

    imgs = []
    for fname, label in panels:
        f = _source(f"output/figures/{fname}")
        imgs.append((Image.open(f).convert("RGB"), label))
    height = 760
    resized = [(im.resize((max(1, int(im.width * height / im.height)), height)), lab)
               for im, lab in imgs]
    gap, label_h, pad = 44, 78, 34
    total_w = sum(im.width for im, _ in resized) + gap * 2 + pad * 2
    canvas = Image.new("RGB", (total_w, height + label_h + pad * 2), _NOIR_BG)
    draw = ImageDraw.Draw(canvas)
    font = scaled_font(canvas.height, 0.072)
    x = pad
    for im, label in resized:
        lw = draw.textlength(label, font=font)
        draw.text((x + (im.width - lw) / 2, pad), label, fill=_NOIR_RED, font=font)
        canvas.paste(im, (x, pad + label_h))
        x += im.width + gap
    _ASSETS.mkdir(parents=True, exist_ok=True)
    out = _ASSETS / "lambda_sweep.png"
    canvas.save(out)
    return out


def _architecture() -> Path:
    """Render a diagram of the paper's codebase from required source inputs."""
    from democreate.animation.diagram import (
        DiagramNode,
        render_architecture_diagram,
    )
    from democreate.codebase.walker import walk_repository
    from democreate.paper.script import _group_modules

    mods = walk_repository(_source("src"))
    columns = [(name, [DiagramNode(label=m) for m in items])
               for name, items in _group_modules(mods)]
    if not columns:
        raise ValueError("Required paper source contains no modules")
    _ASSETS.mkdir(parents=True, exist_ok=True)
    out = _ASSETS / "architecture.png"
    render_architecture_diagram(
        (1920, 1080), title="The Paper's Codebase", columns=columns).save(out)
    return out


def build(paper_root: Path) -> Demo:
    """Construct the curated paper showcase (1080p) — concise, show-don't-tell."""
    global _PAPER_ROOT
    _PAPER_ROOT = paper_root.resolve()
    # Admit all external inputs before staging even the first PDF or image.
    for relative in (
        _PDF_INPUT, "src",
        *(f"output/figures/{name}" for name in _FIGURE_INPUTS),
    ):
        _source(relative)
    pdf = _stage(_source(_PDF_INPUT))
    sweep = _lambda_sweep()
    arch = _architecture()

    scenes: list[Scene] = [
        # --- Setup -------------------------------------------------------
        _slide("hero", "The Question",
               "Many decision streams, one body — two hands, two eyes, a teammate, "
               "a long horizon. How do they stay coordinated?",
               title="Policy Entanglement", subtitle="in Active Inference"),

        _slide("problem", "The Problem",
               "Standard active inference assumes the streams are independent. "
               "Cheap to compute — but independence cannot coordinate.",
               title="The convenient lie of independence",
               bullets=[
                   "Many streams: effectors, senses, other agents, planning horizons.",
                   "Standard models treat each stream as independent.",
                   "Independence erases the dependencies coordination needs.",
               ]),

        _slide("idea", "The Idea",
               "One scalar coupling, lambda, deforms the independent posterior, with "
               "explicit compatibility and preference potentials. At zero, ordinary "
               "active inference; turn it up, and the streams entangle.",
               title="One knob: policy entanglement",
               bullets=[
                   "A scalar coupling lambda, plus compatibility and preference potentials.",
                   "Cross-stream dependence becomes a first-class object, not a factorization artifact.",
                   "lambda equals zero recovers mean-field active inference, exactly.",
               ]),

        _slide("glance", "At a Glance",
               "A claim-strength ledger keeps it honest: exact recoveries, parameterized "
               "embeddings, numerical witnesses, and structural analogies never blur "
               "together. The central identity is machine-checked in Lean.",
               title="The paper at a glance",
               stats=[("λ", "one coupling knob"), ("47", "figures"), ("6", "parts"),
                      ("Lean", "machine-checked"), ("0", "= mean-field")]),
    ]

    # --- Show the knob -------------------------------------------------
    if sweep is not None:
        scenes.append(_slide(
            "sweep", "Turn the Knob",
            "Lambda from zero to four: the joint goes from a product of independent "
            "marginals to mass locked on the aligned diagonal.",
            title="Turn the knob", bg=sweep))

    # --- The argument, in figures (tight, interpretive) ----------------
    scenes += [
        _figure("fig-joint", "Hidden in the Joint", "joint_heatmap_lambda2.png",
                "Each stream alone — the side bars — barely moves. The coordination "
                "lives only in the joint, and the free-energy ledger names its exact "
                "price: the multi-information of leaving independence."),

        _figure("fig-mi", "Proven, Then Witnessed", "ising_mi_curve.png",
                "Machine precision, not hand-waving. Closed-form mutual information "
                "against a brute-force sampler — the residual sits below ten to the "
                "minus fifteen. The central identity is proven in Lean; everything "
                "else is witnessed numerically, like this."),

        _figure("fig-lambdastar", "Coordination on Demand", "optimal_lambda.png",
                "Any target alignment has a closed-form coupling — lambda-star equals "
                "two arctanh of delta over delta-max. Solve it; don't search."),

        _figure("fig-tax", "Coordination Has a Price", "coupling_tax_quadratic.png",
                "Entanglement costs information. Coupling pays only above the line, "
                "where utility clears the multi-information tax. Below it, stay independent."),

        _figure("fig-geodesic", "A Principled Path", "log_weight_flow.png",
                "Every log-weight runs dead-straight in lambda, to floating-point "
                "precision — an exponential geodesic away from the mean-field "
                "submanifold, with a projection identity that snaps the coupled "
                "posterior back to its independent marginals."),

        _figure("fig-archetypes", "It Collapses to a Few Modes",
                "archetype_dendrogram.png",
                "More coupling concentrates the mass, it does not spread it. A handful "
                "of Schmidt archetypes carry almost all the probability."),

        _figure("fig-scale", "And It Scales", "multi_k_tt_rank_profile.png",
                "Five streams, not two: the bond dimension stays at most three. Borrowed "
                "from tensor networks, coordination represents cheaply at any K."),

        _figure("fig-phase", "When to Act as One", "phase_diagram.png",
                "The optimal coupling across payoff and competition — a phase diagram "
                "for when to act as one, and when to stay apart."),

        _figure("fig-pymdp", "Not Just Theory", "pymdp_coupled_rollout.png",
                "The same coupling, dropped into a pymdp POMDP agent: coordinated "
                "rollouts in a live planning loop, not just equations on a page."),
    ]

    if arch is not None:
        scenes.append(_slide(
            "codebase", "Reproducible",
            "Every figure is reproducible — emitted by the paper's own code, which "
            "implements the theory and checks each claim.",
            title="The Paper's Codebase", bg=arch))

    scenes.append(_slide(
        "outro", "The Bigger Picture",
        "Policy entanglement makes coordination tunable, measurable, and compressible — "
        "linking active inference to products of experts, copula variational inference, "
        "branching-time active inference, and tensor-network compression. One knob; "
        "coordinated action becomes a choice.",
        title="Coordination, as a dial",
        subtitle="Policy Entanglement in Active Inference"))

    return Demo(
        title="Policy Entanglement in Active Inference — A Visual Tour",
        scenes=scenes,
        width=1920,
        height=1080,
        fps=30,
        voice="Daniel",
        metadata={"kind": "paper", "curated": True,
                  "pdf": pdf.relative_to(_EXAMPLES).as_posix(), "version": "0.8.0"},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-root", type=Path, required=True,
                        help="Optional curated paper project; read-only input")
    args = parser.parse_args()
    demo = build(args.paper_root)
    problems = demo.validate()
    if problems:
        raise SystemExit(f"demo invalid: {problems}")
    out = _REPO / "examples" / "democreate_paper_showcase.json"
    out.write_text(demo.to_json(), encoding="utf-8")
    print(f"wrote {out} — {len(demo.scenes)} scenes, {len(demo.iter_chunks())} chunks")


if __name__ == "__main__":
    main()
