"""Assessment primitives — widget-based, click-to-answer, visually distinct from code."""
from __future__ import annotations

import warnings
from typing import Any

import ipywidgets as widgets
from IPython.display import HTML, display

from autoresearch_quantum.teaching.tracker import LearningTracker

# ── Shared style constants ──────────────────────────────────────────────────

_QUIZ_BG = "#f5f0ff"          # light purple — visually distinct from code cells
_QUIZ_BORDER = "#7c4dff"      # purple accent
_CORRECT_BG = "#e8f5e9"
_CORRECT_BORDER = "#4caf50"
_WRONG_BG = "#ffebee"
_WRONG_BORDER = "#f44336"
_CHECKPOINT_OK = "#4caf50"
_CHECKPOINT_WARN = "#ff9800"
_CHECKPOINT_BAD = "#f44336"


def _feedback_html(correct: bool, text: str) -> str:
    if correct:
        return (
            f'<div style="border-left:4px solid {_CORRECT_BORDER}; padding:8px 12px; '
            f'margin:8px 0; background:{_CORRECT_BG}; border-radius:4px;">'
            f'<strong style="color:#2e7d32;">&#10003; Correct!</strong> {text}</div>'
        )
    return (
        f'<div style="border-left:4px solid {_WRONG_BORDER}; padding:8px 12px; '
        f'margin:8px 0; background:{_WRONG_BG}; border-radius:4px;">'
        f'<strong style="color:#c62828;">&#10007; Not quite.</strong> {text}</div>'
    )


def _neutral_html(text: str) -> str:
    return (
        f'<div style="border-left:4px solid #2196f3; padding:8px 12px; '
        f'margin:8px 0; background:#e3f2fd; border-radius:4px;">{text}</div>'
    )


# ── quiz: the universal widget-based question ──────────────────────────────


def quiz(
    tracker: LearningTracker,
    qid: str,
    question: str,
    options: list[str],
    correct: int,
    bloom: str = "remember",
    explanation: str = "",
    section: str | None = None,
) -> None:
    """Render a multiple-choice quiz as a styled widget with radio buttons.

    Parameters
    ----------
    question : The question text (supports HTML / MathJax).
    options : List of option strings, e.g. ["pi/2", "pi/4", "pi/8"].
    correct : Zero-based index of the correct option.
    """
    if section:
        tracker.set_section(section)

    # Question header
    header = widgets.HTML(
        f'<div style="font-size:14px; font-weight:600; color:#4a148c; margin-bottom:8px;">'
        f'&#9997; {question}</div>'
    )

    # Radio buttons
    radio = widgets.RadioButtons(
        options=options,
        value=None,
        layout=widgets.Layout(width="auto"),
        style={"description_width": "0px"},
    )

    # Feedback area (hidden until submit)
    feedback = widgets.HTML("")

    # Submit button
    btn = widgets.Button(
        description="Submit",
        button_style="primary",
        icon="check",
        layout=widgets.Layout(width="120px", margin="8px 0 0 0"),
    )

    def on_submit(_: Any) -> None:
        if radio.value is None:
            feedback.value = _neutral_html("Please select an answer first.")
            return
        chosen_idx = options.index(radio.value)
        is_correct = chosen_idx == correct
        fb_text = f"The answer is <b>{options[correct]}</b>. {explanation}"
        feedback.value = _feedback_html(is_correct, fb_text)
        tracker.record(qid, bloom, is_correct, radio.value, options[correct], feedback=fb_text)
        btn.disabled = True
        btn.description = "Done"
        btn.icon = "check" if is_correct else "times"
        radio.disabled = True

    btn.on_click(on_submit)

    box = widgets.VBox(
        [header, radio, btn, feedback],
        layout=widgets.Layout(
            border=f"2px solid {_QUIZ_BORDER}",
            padding="16px",
            margin="12px 0",
            border_radius="10px",
            background_color=_QUIZ_BG,
        ),
    )
    display(box)  # type: ignore[no-untyped-call]


# ── predict: prediction before running next cell ────────────────────────────


def predict_choice(
    tracker: LearningTracker,
    qid: str,
    question: str,
    options: list[str],
    correct: int,
    bloom: str = "understand",
    explanation: str = "",
    section: str | None = None,
) -> None:
    """Two-phase prediction quiz: student picks a prediction, then clicks Reveal to see reality.

    Use this instead of the old predict/check_prediction pair.
    The student predicts the outcome BEFORE running the next code cell.
    """
    if section:
        tracker.set_section(section)

    header = widgets.HTML(
        f'<div style="font-size:14px; font-weight:600; color:#e65100; margin-bottom:8px;">'
        f'&#128300; Predict: {question}</div>'
        f'<div style="font-size:12px; color:#666; margin-bottom:8px;">'
        f'<em>Select your prediction, then run the next code cell, then click Reveal.</em></div>'
    )

    radio = widgets.RadioButtons(
        options=options,
        value=None,
        layout=widgets.Layout(width="auto"),
        style={"description_width": "0px"},
    )

    feedback = widgets.HTML("")

    btn = widgets.Button(
        description="Reveal",
        button_style="warning",
        icon="eye",
        layout=widgets.Layout(width="120px", margin="8px 0 0 0"),
    )

    def on_reveal(_: Any) -> None:
        if radio.value is None:
            feedback.value = _neutral_html("Please select a prediction first.")
            return
        chosen_idx = options.index(radio.value)
        is_correct = chosen_idx == correct
        fb_text = (
            f"You predicted: <b>{radio.value}</b>. "
            f"Actual answer: <b>{options[correct]}</b>. {explanation}"
        )
        feedback.value = _feedback_html(is_correct, fb_text)
        tracker.record(qid, bloom, is_correct, radio.value, options[correct], feedback=fb_text)
        btn.disabled = True
        btn.description = "Revealed"
        radio.disabled = True

    btn.on_click(on_reveal)

    box = widgets.VBox(
        [header, radio, btn, feedback],
        layout=widgets.Layout(
            border="2px solid #ff9800",
            padding="16px",
            margin="12px 0",
            border_radius="10px",
            background_color="#fff8e1",
        ),
    )
    display(box)  # type: ignore[no-untyped-call]


# ── reflect: free-response with model answer reveal ─────────────────────────


def reflect(
    tracker: LearningTracker,
    qid: str,
    question: str,
    model_answer: str = "",
    bloom: str = "evaluate",
    section: str | None = None,
) -> None:
    """Free-text reflection with a Reveal Model Answer button."""
    if section:
        tracker.set_section(section)

    header = widgets.HTML(
        f'<div style="font-size:14px; font-weight:600; color:#1565c0; margin-bottom:8px;">'
        f'&#128221; {question}</div>'
    )

    text_area = widgets.Textarea(
        placeholder="Type your thoughts here...",
        layout=widgets.Layout(width="100%", height="80px"),
    )

    feedback = widgets.HTML("")

    btn = widgets.Button(
        description="Show Model Answer",
        button_style="info",
        icon="lightbulb-o",
        layout=widgets.Layout(width="200px", margin="8px 0 0 0"),
    )

    def on_reveal(_: Any) -> None:
        student_text = text_area.value.strip()
        if not student_text:
            feedback.value = _neutral_html("Write your answer first, then reveal the model answer.")
            return
        tracker.record(qid, bloom, None, student_text, model_answer, feedback="self-assessed")
        if model_answer:
            feedback.value = _neutral_html(f"<strong>Model answer:</strong> {model_answer}")
        btn.disabled = True
        text_area.disabled = True

    btn.on_click(on_reveal)

    box = widgets.VBox(
        [header, text_area, btn, feedback],
        layout=widgets.Layout(
            border="2px solid #1565c0",
            padding="16px",
            margin="12px 0",
            border_radius="10px",
            background_color="#e3f2fd",
        ),
    )
    display(box)  # type: ignore[no-untyped-call]


# ── order: drag-free ordering via dropdowns ─────────────────────────────────


def order(
    tracker: LearningTracker,
    qid: str,
    instruction: str,
    items: list[str],
    correct_order: list[str],
    bloom: str = "analyze",
    explanation: str = "",
    section: str | None = None,
    ties: list[list[str]] | None = None,
) -> None:
    """Ordering question using dropdown selects for each position.

    Parameters
    ----------
    ties : Optional list of groups of items that are interchangeable.
           E.g. ties=[["X", "Z"]] means X and Z can appear in either order.
    """
    if section:
        tracker.set_section(section)

    header = widgets.HTML(
        f'<div style="font-size:14px; font-weight:600; color:#6a1b9a; margin-bottom:8px;">'
        f'&#128296; {instruction}</div>'
    )

    dropdowns = []
    for i in range(len(correct_order)):
        dd = widgets.Dropdown(
            options=["(select)"] + items,
            value="(select)",
            description=f"#{i+1}:",
            layout=widgets.Layout(width="400px"),
        )
        dropdowns.append(dd)

    feedback = widgets.HTML("")

    btn = widgets.Button(
        description="Submit",
        button_style="primary",
        icon="check",
        layout=widgets.Layout(width="120px", margin="8px 0 0 0"),
    )

    def _check_order(student: list[str]) -> bool:
        """Check if student order matches, allowing permutations within tied groups."""
        if ties is None:
            return student == correct_order
        # Build a mapping from item -> tie group index
        tie_map: dict[str, int] = {}
        for gi, group in enumerate(ties):
            for item in group:
                tie_map[item] = gi
        # For each position, check the student's item is valid
        # Items in the same tie group can swap positions with each other
        for i, s_item in enumerate(student):
            c_item = correct_order[i]
            if s_item == c_item:
                continue
            if s_item in tie_map and c_item in tie_map and tie_map[s_item] == tie_map[c_item]:
                continue
            return False
        return True

    def on_submit(_: Any) -> None:
        student = [dd.value for dd in dropdowns]
        if "(select)" in student:
            feedback.value = _neutral_html("Please fill in all positions.")
            return
        is_correct = _check_order(student)
        fb_text = (
            f"Your order: <b>{student}</b><br>"
            f"Correct order: <b>{correct_order}</b><br>{explanation}"
        )
        feedback.value = _feedback_html(is_correct, fb_text)
        tracker.record(qid, bloom, is_correct, student, correct_order, feedback=fb_text)
        btn.disabled = True
        for dd in dropdowns:
            dd.disabled = True

    btn.on_click(on_submit)

    box = widgets.VBox(
        [header, *dropdowns, btn, feedback],
        layout=widgets.Layout(
            border=f"2px solid {_QUIZ_BORDER}",
            padding="16px",
            margin="12px 0",
            border_radius="10px",
            background_color=_QUIZ_BG,
        ),
    )
    display(box)  # type: ignore[no-untyped-call]


# ── checkpoint_summary (unchanged — pure HTML) ─────────────────────────────


def checkpoint_summary(tracker: LearningTracker, section: str) -> None:
    """Show a mini-dashboard for just this section."""
    all_data = tracker.score_by_section()
    data = all_data.get(section, {"correct": 0, "incorrect": 0, "total": 0, "pct": 0.0})

    if data["total"] == 0:
        display(HTML(_neutral_html(  # type: ignore[no-untyped-call]
            f"<strong>Checkpoint — {section}:</strong> No scored questions in this section yet."
        )))
        return

    pct = data["pct"]
    colour = _CHECKPOINT_OK if pct >= 70 else _CHECKPOINT_WARN if pct >= 40 else _CHECKPOINT_BAD
    bar = (
        f'<div style="background:#ddd; border-radius:6px; height:18px; margin:4px 0;">'
        f'<div style="background:{colour}; width:{pct}%; height:100%; border-radius:6px;"></div></div>'
    )

    struggled = [
        a.question_id for a in tracker.attempts
        if a.section == section and a.correct is False
    ]
    review = ""
    if struggled:
        review = "<br><em>Review: " + ", ".join(f"<code>{q}</code>" for q in set(struggled)) + "</em>"

    msg = (
        f"<strong>Checkpoint — {section}:</strong> "
        f"{data['correct']}/{data['total']} correct ({pct}%){bar}"
    )
    if pct >= 70:
        msg += "<br>Good grasp of this section. Moving on!"
    elif pct >= 40:
        msg += "<br>Partial understanding — consider re-reading the cells above before continuing."
    else:
        msg += "<br>This section needs more work. Re-read and retry the questions above."
    msg += review

    display(HTML(  # type: ignore[no-untyped-call]
        f'<div style="border:2px solid {colour}; padding:12px 16px; margin:16px 0; '
        f'border-radius:8px; background:#fafafa;">{msg}</div>'
    ))


# ── Backwards-compatible aliases (old API → new API) ────────────────────────
# These allow old notebook cells to still work while we migrate.

def multiple_choice(tracker: LearningTracker, qid: str, question: str,
                    options: dict[str, str], correct: str, answer: str = "?",
                    bloom: str = "remember", explanation: str = "") -> None:
    """Legacy wrapper — redirects to quiz()."""
    opt_list = [f"({k}) {v}" for k, v in options.items()]
    correct_idx = list(options.keys()).index(correct.lower())
    quiz(tracker, qid, question, opt_list, correct_idx, bloom, explanation)

def predict(tracker: LearningTracker, qid: str, question: str,
            your_prediction: str = "?", bloom: str = "understand") -> None:
    """Legacy wrapper — use predict_choice() instead."""
    warnings.warn(
        "predict() is deprecated and does nothing. Use predict_choice() instead.",
        DeprecationWarning, stacklevel=2,
    )

def check_prediction(tracker: LearningTracker, qid: str, actual_value: Any = None,
                     was_correct: bool = False, explanation: str = "") -> None:
    """Legacy wrapper — use predict_choice() instead."""
    warnings.warn(
        "check_prediction() is deprecated and does nothing. Use predict_choice() instead.",
        DeprecationWarning, stacklevel=2,
    )

def numerical_answer(tracker: LearningTracker, qid: str, question: str,
                     answer: float = 0.0, correct: float = 0.0,
                     tolerance: float = 0.01, bloom: str = "apply",
                     explanation: str = "") -> None:
    """Legacy wrapper — use quiz() instead."""
    warnings.warn(
        "numerical_answer() is deprecated and does nothing. Use quiz() instead.",
        DeprecationWarning, stacklevel=2,
    )

def free_response(tracker: LearningTracker, qid: str, question: str,
                  answer: str = "?", bloom: str = "evaluate",
                  model_answer: str = "") -> None:
    """Legacy wrapper — redirects to reflect()."""
    warnings.warn(
        "free_response() is deprecated. Use reflect() directly.",
        DeprecationWarning, stacklevel=2,
    )
    reflect(tracker, qid, question, model_answer, bloom)

def code_challenge(tracker: LearningTracker, qid: str, description: str,
                   test_passed: bool = False, bloom: str = "apply",
                   hint: str = "", explanation: str = "") -> None:
    """Legacy wrapper — no replacement; use code cells with assertions."""
    warnings.warn(
        "code_challenge() is deprecated and does nothing. Use code cells with assertions.",
        DeprecationWarning, stacklevel=2,
    )

def concept_sort(tracker: LearningTracker, qid: str, instruction: str,
                 student_order: list[str] | None = None,
                 correct_order: list[str] | None = None, bloom: str = "analyze",
                 explanation: str = "") -> None:
    """Legacy wrapper — use order() instead."""
    warnings.warn(
        "concept_sort() is deprecated. Use order() directly.",
        DeprecationWarning, stacklevel=2,
    )
    if correct_order:
        order(tracker, qid, instruction, list(correct_order), list(correct_order), bloom, explanation)
