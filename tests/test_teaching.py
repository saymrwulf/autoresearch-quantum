"""Tests for the teaching layer: assess.py and tracker.py."""
from __future__ import annotations

import json
import warnings
from unittest.mock import MagicMock, patch

import pytest

from autoresearch_quantum.teaching.tracker import LearningTracker

# ============================================================================
#  LearningTracker — core logic
# ============================================================================

class TestLearningTracker:
    def test_init(self):
        t = LearningTracker("test_nb")
        assert t.notebook_id == "test_nb"
        assert t.attempts == []
        assert t.current_section == "intro"

    def test_set_section(self):
        t = LearningTracker("test_nb")
        t.set_section("stabilisers")
        assert t.current_section == "stabilisers"

    def test_record_appends_attempt(self):
        t = LearningTracker("test_nb")
        t.set_section("sec1")
        t.record("q1", "remember", True, "A", "A")
        assert len(t.attempts) == 1
        a = t.attempts[0]
        assert a.question_id == "q1"
        assert a.bloom_level == "remember"
        assert a.correct is True
        assert a.section == "sec1"
        assert a.attempt_number == 1

    def test_record_increments_attempt_number(self):
        t = LearningTracker("test_nb")
        t.record("q1", "remember", False, "B", "A")
        t.record("q1", "remember", True, "A", "A")
        assert t.attempts[0].attempt_number == 1
        assert t.attempts[1].attempt_number == 2

    def test_record_none_correct_for_reflections(self):
        t = LearningTracker("test_nb")
        t.record("r1", "evaluate", None, "my thoughts", "model answer")
        assert t.attempts[0].correct is None


class TestScoreBySection:
    def test_empty_tracker(self):
        t = LearningTracker("test_nb")
        assert t.score_by_section() == {}

    def test_single_correct(self):
        t = LearningTracker("test_nb")
        t.set_section("sec1")
        t.record("q1", "remember", True, "A", "A")
        result = t.score_by_section()
        assert result["sec1"]["correct"] == 1
        assert result["sec1"]["total"] == 1
        assert result["sec1"]["pct"] == 100.0

    def test_mixed_results(self):
        t = LearningTracker("test_nb")
        t.set_section("sec1")
        t.record("q1", "remember", True, "A", "A")
        t.record("q2", "understand", False, "B", "A")
        result = t.score_by_section()
        assert result["sec1"]["correct"] == 1
        assert result["sec1"]["incorrect"] == 1
        assert result["sec1"]["total"] == 2
        assert result["sec1"]["pct"] == 50.0

    def test_latest_attempt_wins(self):
        """Only the latest attempt per question should count."""
        t = LearningTracker("test_nb")
        t.set_section("sec1")
        t.record("q1", "remember", False, "B", "A")
        t.record("q1", "remember", True, "A", "A")
        result = t.score_by_section()
        assert result["sec1"]["correct"] == 1
        assert result["sec1"]["incorrect"] == 0
        assert result["sec1"]["total"] == 1

    def test_none_correct_excluded(self):
        """Reflections (correct=None) should not appear in section scores."""
        t = LearningTracker("test_nb")
        t.set_section("sec1")
        t.record("r1", "evaluate", None, "my thoughts", "model")
        assert t.score_by_section() == {}

    def test_multiple_sections(self):
        t = LearningTracker("test_nb")
        t.set_section("sec1")
        t.record("q1", "remember", True, "A", "A")
        t.set_section("sec2")
        t.record("q2", "apply", False, "B", "A")
        result = t.score_by_section()
        assert "sec1" in result
        assert "sec2" in result
        assert result["sec1"]["pct"] == 100.0
        assert result["sec2"]["pct"] == 0.0


class TestScoreByBloom:
    def test_groups_by_bloom(self):
        t = LearningTracker("test_nb")
        t.record("q1", "remember", True, "A", "A")
        t.record("q2", "apply", False, "B", "A")
        result = t.score_by_bloom()
        assert result["remember"]["correct"] == 1
        assert result["apply"]["correct"] == 0


class TestStruggledQuestions:
    def test_no_struggles(self):
        t = LearningTracker("test_nb")
        t.record("q1", "remember", True, "A", "A")
        assert t.struggled_questions() == []

    def test_wrong_answer_is_struggled(self):
        t = LearningTracker("test_nb")
        t.record("q1", "remember", False, "B", "A")
        assert "q1" in t.struggled_questions()

    def test_multiple_attempts_is_struggled(self):
        t = LearningTracker("test_nb")
        t.record("q1", "remember", False, "B", "A")
        t.record("q1", "remember", True, "A", "A")
        assert "q1" in t.struggled_questions()


class TestMasteryScore:
    def test_empty(self):
        t = LearningTracker("test_nb")
        assert t.mastery_score() == 0.0

    def test_perfect(self):
        t = LearningTracker("test_nb")
        t.record("q1", "remember", True, "A", "A")
        t.record("q2", "understand", True, "B", "B")
        assert t.mastery_score() == 100.0

    def test_partial(self):
        t = LearningTracker("test_nb")
        t.record("q1", "remember", True, "A", "A")
        t.record("q2", "understand", False, "B", "A")
        assert t.mastery_score() == 50.0


class TestSave:
    def test_save_to_explicit_path(self, tmp_path):
        t = LearningTracker("test_nb")
        t.record("q1", "remember", True, "A", "A")
        out = t.save(tmp_path / "progress.json")
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["notebook_id"] == "test_nb"
        assert data["mastery_score"] == 100.0
        assert len(data["attempts"]) == 1

    def test_save_to_save_dir(self, tmp_path):
        t = LearningTracker("test_nb", save_dir=tmp_path)
        t.record("q1", "remember", True, "A", "A")
        out = t.save()
        assert out == tmp_path / "test_nb_progress.json"
        assert out.exists()

    def test_save_default_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        t = LearningTracker("test_nb")
        t.record("q1", "remember", True, "A", "A")
        out = t.save()
        assert out.name == "test_nb_progress.json"
        assert out.exists()


# ============================================================================
#  assess.py — widget functions
# ============================================================================

# We mock ipywidgets and IPython.display since we're not running in a notebook.

@pytest.fixture
def mock_display():
    """Mock IPython display to capture display calls."""
    with patch("autoresearch_quantum.teaching.assess.display") as mock_d:
        yield mock_d


@pytest.fixture
def mock_widgets():
    """Mock ipywidgets so we can test widget construction logic."""
    with patch("autoresearch_quantum.teaching.assess.widgets") as mock_w:
        # Make VBox return a MagicMock that we can track
        mock_w.VBox.return_value = MagicMock(name="VBox")
        mock_w.HTML.return_value = MagicMock(name="HTML")
        mock_w.RadioButtons.return_value = MagicMock(name="RadioButtons", value=None)
        mock_w.Button.return_value = MagicMock(name="Button")
        mock_w.Textarea.return_value = MagicMock(name="Textarea", value="")
        mock_w.Dropdown.return_value = MagicMock(name="Dropdown", value="(select)")
        mock_w.Layout.return_value = MagicMock(name="Layout")
        yield mock_w


class TestQuiz:
    def test_returns_none(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import quiz
        t = LearningTracker("test")
        result = quiz(t, "q1", "What?", ["A", "B"], 0, section="s1")
        assert result is None

    def test_displays_exactly_once(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import quiz
        t = LearningTracker("test")
        quiz(t, "q1", "What?", ["A", "B"], 0)
        assert mock_display.call_count == 1

    def test_sets_section(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import quiz
        t = LearningTracker("test")
        quiz(t, "q1", "What?", ["A", "B"], 0, section="mysec")
        assert t.current_section == "mysec"

    def test_submit_correct_records(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import quiz
        t = LearningTracker("test")
        mock_btn = mock_widgets.Button.return_value
        mock_radio = mock_widgets.RadioButtons.return_value

        quiz(t, "q1", "What?", ["A", "B"], 0, bloom="remember")

        # Simulate user selecting correct answer and clicking submit
        mock_radio.value = "A"
        # Get the on_click callback
        on_click_call = mock_btn.on_click.call_args
        callback = on_click_call[0][0]
        callback(None)

        assert len(t.attempts) == 1
        assert t.attempts[0].correct is True
        assert t.attempts[0].student_answer == "A"

    def test_submit_incorrect_records(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import quiz
        t = LearningTracker("test")
        mock_btn = mock_widgets.Button.return_value
        mock_radio = mock_widgets.RadioButtons.return_value

        quiz(t, "q1", "What?", ["A", "B"], 0, bloom="remember")

        mock_radio.value = "B"
        callback = mock_btn.on_click.call_args[0][0]
        callback(None)

        assert t.attempts[0].correct is False


class TestPredictChoice:
    def test_returns_none(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import predict_choice
        t = LearningTracker("test")
        result = predict_choice(t, "q1", "Predict?", ["A", "B"], 0)
        assert result is None

    def test_displays_exactly_once(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import predict_choice
        t = LearningTracker("test")
        predict_choice(t, "q1", "Predict?", ["A", "B"], 0)
        assert mock_display.call_count == 1


class TestReflect:
    def test_returns_none(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import reflect
        t = LearningTracker("test")
        result = reflect(t, "r1", "What do you think?")
        assert result is None

    def test_displays_exactly_once(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import reflect
        t = LearningTracker("test")
        reflect(t, "r1", "What do you think?")
        assert mock_display.call_count == 1


class TestOrder:
    def test_returns_none(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import order
        t = LearningTracker("test")
        result = order(t, "o1", "Sort these:", ["A", "B"], ["A", "B"])
        assert result is None

    def test_displays_exactly_once(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import order
        t = LearningTracker("test")
        order(t, "o1", "Sort:", ["A", "B"], ["A", "B"])
        assert mock_display.call_count == 1

    def test_order_check_exact(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import order
        t = LearningTracker("test")

        # We need to test the _check_order logic. Since it's nested,
        # we test via the submit callback.
        mock_btn = mock_widgets.Button.return_value

        # Create two dropdowns that will return values
        dd1 = MagicMock(value="A", disabled=False)
        dd2 = MagicMock(value="B", disabled=False)
        mock_widgets.Dropdown.side_effect = [dd1, dd2]

        order(t, "o1", "Sort:", ["A", "B"], ["A", "B"])

        callback = mock_btn.on_click.call_args[0][0]
        callback(None)

        assert len(t.attempts) == 1
        assert t.attempts[0].correct is True

    def test_order_check_with_ties(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import order
        t = LearningTracker("test")
        mock_btn = mock_widgets.Button.return_value

        # Student puts Z before X (tied, so should be correct)
        dd1 = MagicMock(value="Z", disabled=False)
        dd2 = MagicMock(value="X", disabled=False)
        dd3 = MagicMock(value="Y", disabled=False)
        mock_widgets.Dropdown.side_effect = [dd1, dd2, dd3]

        order(t, "o1", "Sort:", ["X", "Z", "Y"], ["X", "Z", "Y"],
              ties=[["X", "Z"]])

        callback = mock_btn.on_click.call_args[0][0]
        callback(None)

        assert t.attempts[0].correct is True

    def test_order_check_wrong(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import order
        t = LearningTracker("test")
        mock_btn = mock_widgets.Button.return_value

        dd1 = MagicMock(value="Y", disabled=False)
        dd2 = MagicMock(value="X", disabled=False)
        dd3 = MagicMock(value="Z", disabled=False)
        mock_widgets.Dropdown.side_effect = [dd1, dd2, dd3]

        order(t, "o1", "Sort:", ["X", "Z", "Y"], ["X", "Z", "Y"])

        callback = mock_btn.on_click.call_args[0][0]
        callback(None)

        assert t.attempts[0].correct is False


class TestCheckpointSummary:
    def test_displays_html(self, mock_display):
        with patch("autoresearch_quantum.teaching.assess.HTML"):
            from autoresearch_quantum.teaching.assess import checkpoint_summary
            t = LearningTracker("test")
            t.set_section("sec1")
            t.record("q1", "remember", True, "A", "A")
            checkpoint_summary(t, "sec1")
            assert mock_display.call_count == 1


# ============================================================================
#  Legacy wrappers — deprecation warnings
# ============================================================================

class TestLegacyWrappers:
    def test_predict_warns(self):
        from autoresearch_quantum.teaching.assess import predict
        t = LearningTracker("test")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            predict(t, "q1", "What?")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "predict_choice" in str(w[0].message)

    def test_check_prediction_warns(self):
        from autoresearch_quantum.teaching.assess import check_prediction
        t = LearningTracker("test")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_prediction(t, "q1")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_numerical_answer_warns(self):
        from autoresearch_quantum.teaching.assess import numerical_answer
        t = LearningTracker("test")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            numerical_answer(t, "q1", "How many?")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_code_challenge_warns(self):
        from autoresearch_quantum.teaching.assess import code_challenge
        t = LearningTracker("test")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            code_challenge(t, "q1", "Do X")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_free_response_warns_and_redirects(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import free_response
        t = LearningTracker("test")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            free_response(t, "q1", "Explain?", model_answer="Because X")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            # Should still display a reflect widget
            assert mock_display.call_count == 1

    def test_concept_sort_warns_and_redirects(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import concept_sort
        t = LearningTracker("test")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            concept_sort(t, "q1", "Sort:", correct_order=["A", "B"])
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert mock_display.call_count == 1

    def test_multiple_choice_redirects(self, mock_display, mock_widgets):
        from autoresearch_quantum.teaching.assess import multiple_choice
        t = LearningTracker("test")
        # multiple_choice is not deprecated (it works), just redirects
        multiple_choice(t, "q1", "What?", {"a": "Alpha", "b": "Beta"}, "a")
        assert mock_display.call_count == 1
