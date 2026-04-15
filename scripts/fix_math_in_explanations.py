r"""Fix math notation in explanation strings across all enhanced notebooks.

Replaces raw pseudo-LaTeX in HTML explanation text with proper MathJax \(...\)
delimiters so Jupyter renders them correctly.
"""
import json
from pathlib import Path

NOTEBOOKS = [
    "notebooks/plan_a/01_encoded_magic_state.ipynb",
    "notebooks/plan_a/02_measuring_progress.ipynb",
    "notebooks/plan_a/03_the_ratchet.ipynb",
    "notebooks/plan_b/spiral_notebook.ipynb",
    "notebooks/plan_c/00_dashboard.ipynb",
    "notebooks/plan_c/track_a_physics.ipynb",
    "notebooks/plan_c/track_b_engineering.ipynb",
    "notebooks/plan_c/track_c_search.ipynb",
]

# Replacements: (raw text, MathJax or clean English)
REPLACEMENTS = [
    # T-state formula
    ("(|0> + e^{i*pi/4}|1>)/sqrt(2)", r"\\(( |0\\rangle + e^{i\\pi/4} |1\\rangle ) / \\sqrt{2}\\)"),
    ("(|0> + e^{i*pi/4}|1>)/\\sqrt(2)", r"\\(( |0\\rangle + e^{i\\pi/4} |1\\rangle ) / \\sqrt{2}\\)"),

    # Global phase
    ("e^{i*theta}|psi>", r"\\(e^{i\\theta}|\\psi\\rangle\\)"),
    ("e^{i*theta}", r"\\(e^{i\\theta}\\)"),
    ("A global phase e^{i*theta}|psi> is physically indistinguishable from |psi>.",
     r"A global phase \\(e^{i\\theta}|\\psi\\rangle\\) is physically indistinguishable from \\(|\\psi\\rangle\\)."),
    ("A global phase factor e^{i*theta} multiplies all amplitudes but has no observable consequence",
     r"A global phase factor \\(e^{i\\theta}\\) multiplies all amplitudes but has no observable consequence"),

    # Stabilizer notation
    ("Z anti-commutes with X (ZX = -XZ).",
     r"Z anti-commutes with X (\\(ZX = -XZ\\))."),
    ("Conjugating XXXX by Z_0 gives -XXXX (one anti-commutation).",
     r"Conjugating \\(XXXX\\) by \\(Z_0\\) gives \\(-XXXX\\) (one anti-commutation)."),

    # Y = iXZ
    ("Y = iXZ, so it anti-commutes with both XXXX (because of the Z part) and ZZZZ (because of the X part).",
     r"\\(Y = iXZ\\), so it anti-commutes with both \\(XXXX\\) (because of the Z part) and \\(ZZZZ\\) (because of the X part)."),

    # Logical qubits
    ("|0>_L and |1>_L", r"\\(|0\\rangle_L\\) and \\(|1\\rangle_L\\)"),
    ("|0>_L", r"\\(|0\\rangle_L\\)"),
    ("|1>_L", r"\\(|1\\rangle_L\\)"),

    # pi/4 in explanations (only in explanation context, not in options)
    ("The phase pi/4 = 45 degrees is what makes it a",
     r"The phase \\(\\pi/4 = 45°\\) is what makes it a"),
    ("The phase pi/4 = 45 degrees gives the state its name",
     r"The phase \\(\\pi/4 = 45°\\) gives the state its name"),
    ("Note: pi/8 is often mentioned because T = diag(1, e^{i*pi/4}) and pi/4 = 2*(pi/8).",
     r"Note: \\(\\pi/8\\) is often mentioned because \\(T = \\text{diag}(1, e^{i\\pi/4})\\) and \\(\\pi/4 = 2 \\times (\\pi/8)\\)."),

    # sqrt(2) in running text
    ("1/sqrt(2)", r"\\(1/\\sqrt{2}\\)"),
    ("(lx + ly)/sqrt(2)", r"\\((l_x + l_y)/\\sqrt{2}\\)"),

    # Witness formula fragments
    ("magic_factor = (1 + (1/sqrt(2) + 1/sqrt(2))/sqrt(2)) / 2 = (1 + 1) / 2 = 1.0.",
     r"magic\\_factor = \\((1 + (1/\\sqrt{2} + 1/\\sqrt{2})/\\sqrt{2}) / 2 = (1+1)/2 = 1.0\\)."),
    ("W = [(1 + (0+0)/sqrt(2))/2] * [(1+1)/2] = (1/2) * 1 = 0.5.",
     r"\\(W = \\frac{1 + (0+0)/\\sqrt{2}}{2} \\times \\frac{1+1}{2} = 0.5\\)."),

    # Cost formula
    ("$w_{2q} = 0.08$", r"\\(w_{2q} = 0.08\\)"),
    ("$n$ two-qubit gates", r"\\(n\\) two-qubit gates"),
    ("$0.08 \\times n$", r"\\(0.08 \\times n\\)"),

    # d-1 errors
    ("up to d-1 errors", r"up to \\(d{-}1\\) errors"),
    ("can detect errors on up to d-1 qubits", r"can detect up to \\(d{-}1\\) qubit errors"),

    # Score formula in text
    ("score = quality * acceptance_rate / cost",
     r"\\(\\text{score} = \\text{quality} \\times \\text{acceptance\\_rate} \\,/\\, \\text{cost}\\)"),
    ("score = quality * acceptance / cost",
     r"\\(\\text{score} = \\text{quality} \\times \\text{acceptance} \\,/\\, \\text{cost}\\)"),

    # The |<X>| notation
    ("|<X>| = |<Y>| = 1/sqrt(2) ~ 0.707 and <Z> = 0",
     r"\\(|\\langle X\\rangle| = |\\langle Y\\rangle| = 1/\\sqrt{2} \\approx 0.707\\) and \\(\\langle Z\\rangle = 0\\)"),
]


def fix_cell_source(source_lines: list[str]) -> list[str]:
    """Apply all replacements to the joined source, then re-split."""
    text = "".join(source_lines)
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    # Re-split preserving the original line structure
    if not text:
        return source_lines
    lines = text.split("\n")
    return [line + "\n" for line in lines[:-1]] + [lines[-1]]


total_changes = 0
for nb_path_str in NOTEBOOKS:
    nb_path = Path(nb_path_str)
    if not nb_path.exists():
        print(f"SKIP (not found): {nb_path}")
        continue

    nb = json.loads(nb_path.read_text())
    changes = 0

    for cell in nb["cells"]:
        old_src = "".join(cell["source"])
        cell["source"] = fix_cell_source(cell["source"])
        new_src = "".join(cell["source"])
        if old_src != new_src:
            changes += 1

    if changes:
        nb_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
        print(f"Fixed {changes} cells in {nb_path}")
        total_changes += changes
    else:
        print(f"No changes needed in {nb_path}")

print(f"\nTotal: {total_changes} cells fixed across {len(NOTEBOOKS)} notebooks")
