"""
quiz_engine.py

Core logic for the IAAO 102 flashcard/quiz app: data loading, answer grading,
multiple-choice generation, attempt logging, and the interactive ipywidgets
QuizApp itself.

The notebook (IAAO_102_Quiz.ipynb) only imports from this module and runs
QuizApp() - it holds no quiz logic of its own. To add a new chapter, drop a
chN_flashcards.json file into DATA_DIR following the same schema as the
existing files; no changes to this module or the notebook are required.
"""

import json
import random
import csv
import os
from datetime import datetime

import ipywidgets as widgets
from IPython.display import display, clear_output

DATA_DIR = "data"
LOG_PATH = os.path.join(DATA_DIR, "attempts_log.csv")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_chapter(chapter_num):
    path = os.path.join(DATA_DIR, f"ch{chapter_num}_flashcards.json")
    with open(path, "r") as f:
        return json.load(f)


def available_chapters():
    chapters = []
    if os.path.isdir(DATA_DIR):
        for fname in sorted(os.listdir(DATA_DIR)):
            if fname.startswith("ch") and fname.endswith("_flashcards.json"):
                try:
                    chapters.append(int(fname[2:fname.index("_")]))
                except ValueError:
                    pass
    return sorted(chapters)


# ---------------------------------------------------------------------------
# Grading logic
# ---------------------------------------------------------------------------

def normalize(s):
    return " ".join(s.strip().lower().replace("-", " ").split())


def check_fill_in(card, user_answer):
    accepted = {normalize(card["answer"])}
    for alt in card.get("accept", []):
        accepted.add(normalize(alt))
    return normalize(user_answer) in accepted


def check_fill_in_multi(card, user_answers):
    """Order-independent match of blanks against card['answers']."""
    targets = [normalize(a) for a in card["answers"]]
    given = [normalize(a) for a in user_answers if a.strip()]
    if len(given) != len(targets):
        return False
    remaining = targets.copy()
    for g in given:
        if g in remaining:
            remaining.remove(g)
        else:
            return False
    return len(remaining) == 0


def check_list(card, user_items):
    """Strict match: every required item must be present (allowing known
    variant spellings from card['accept_variants']). Returns
    (all_matched: bool, matched_items: set)."""
    variants = card.get("accept_variants", {})
    given = set(normalize(i) for i in user_items if i.strip())
    matched = set()
    for item in card["items"]:
        acceptable = {normalize(item)} | set(normalize(v) for v in variants.get(item, []))
        if given & acceptable:
            matched.add(item)
    return len(matched) == len(card["items"]), matched


def check_mc(card, selected):
    correct = card.get("answer")
    if correct is None and "answers" in card:
        correct = card["answers"][0]
    return normalize(selected) == normalize(correct)


# ---------------------------------------------------------------------------
# Multiple-choice option generation
# ---------------------------------------------------------------------------

def build_mc_options(card, pool, n_options=4):
    correct = card.get("answer")
    if correct is None:
        correct = card["items"][0] if card["type"] == "list" else (
            card["answers"][0] if "answers" in card else ""
        )
    distractors = [d for d in pool if normalize(d) != normalize(correct)]
    random.shuffle(distractors)
    options = [correct] + distractors[: max(0, n_options - 1)]
    random.shuffle(options)
    return options


# ---------------------------------------------------------------------------
# Attempt logging
# ---------------------------------------------------------------------------

def ensure_log():
    if not os.path.exists(LOG_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "chapter", "mode", "score", "total", "pct", "missed_question_ids"])


def log_session(chapter, mode, score, total, missed_ids):
    """Write ONE row summarizing a fully-completed quiz session.

    Only called from show_summary(), which only runs once the full deck has
    been exhausted - so partial/incomplete runs (notebook closed mid-deck,
    kernel restarted, etc.) are never written at all.
    """
    ensure_log()
    pct = round(100 * score / total, 1) if total else 0.0
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            chapter,
            mode,
            score,
            total,
            pct,
            ";".join(missed_ids),
        ])


# ---------------------------------------------------------------------------
# Quiz app (ipywidgets UI)
# ---------------------------------------------------------------------------

class QuizApp:
    def __init__(self):
        self.chapter_dd = widgets.Dropdown(options=available_chapters(), description="Chapter:")
        self.mode_rb = widgets.RadioButtons(
            options=["Recall (type it yourself)", "Multiple Choice"], description="Mode:"
        )
        self.start_btn = widgets.Button(description="Start Quiz", button_style="success")
        self.start_btn.on_click(self.start_quiz)
        self.setup_box = widgets.VBox([self.chapter_dd, self.mode_rb, self.start_btn])
        self.quiz_area = widgets.Output()
        self.data = None
        self.cards = []
        self.idx = 0
        self.score = 0
        self.results = []

        display(self.setup_box, self.quiz_area)

    def start_quiz(self, _):
        self.data = load_chapter(self.chapter_dd.value)
        self.cards = self.data["cards"]
        random.shuffle(self.cards)
        self.idx = 0
        self.score = 0
        self.results = []
        self.mode = "recall" if self.mode_rb.value.startswith("Recall") else "mc"
        self.render_card()

    def render_card(self):
        with self.quiz_area:
            clear_output()
            if self.idx >= len(self.cards):
                self.show_summary()
                return
            card = self.cards[self.idx]
            print(f"Question {self.idx + 1} of {len(self.cards)}   (Score so far: {self.score})")
            print()
            print(card["prompt"])
            print()

            if self.mode == "recall":
                self._render_recall(card)
            else:
                self._render_mc(card)

    def _render_recall(self, card):
        if card["type"] == "list":
            n = len(card["items"])
            print(f"(List {n} items - one per line)")
            box = widgets.Textarea(
                placeholder="Type one answer per line...",
                layout=widgets.Layout(width="500px", height="120px"),
            )
        elif card["type"] == "fill_in_multi":
            n = len(card["answers"])
            print(f"(Fill in {n} blanks - one per line, in order)")
            box = widgets.Textarea(
                placeholder="blank 1\nblank 2", layout=widgets.Layout(width="500px", height="80px")
            )
        elif card["type"] == "multiple_choice_given":
            box = widgets.RadioButtons(options=card["options"])
        else:
            box = widgets.Text(placeholder="Your answer...", layout=widgets.Layout(width="400px"))

        submit = widgets.Button(description="Submit", button_style="primary")
        feedback = widgets.Output()

        def on_submit(_):
            with feedback:
                clear_output()
                if card["type"] == "list":
                    user_items = box.value.split("\n")
                    correct, matched = check_list(card, user_items)
                    self._record(card, correct)
                    if correct:
                        print("Correct! All items matched.")
                    else:
                        missing = [i for i in card["items"] if i not in matched]
                        print("Incorrect / incomplete.")
                        print("Missing or unmatched:", ", ".join(missing))
                        print("Full correct list:", ", ".join(card["items"]))
                elif card["type"] == "fill_in_multi":
                    user_answers = box.value.split("\n")
                    correct = check_fill_in_multi(card, user_answers)
                    self._record(card, correct)
                    print("Correct!" if correct else f"Incorrect. Correct answers: {', '.join(card['answers'])}")
                elif card["type"] == "multiple_choice_given":
                    correct = check_mc(card, box.value)
                    self._record(card, correct)
                    print("Correct!" if correct else f"Incorrect. Correct answer: {card['answer']}")
                else:
                    correct = check_fill_in(card, box.value)
                    self._record(card, correct)
                    print("Correct!" if correct else f"Incorrect. Correct answer: {card['answer']}")
                next_btn.disabled = False

        submit.on_click(on_submit)
        next_btn = widgets.Button(description="Next", disabled=True)
        next_btn.on_click(lambda _: self.next_card())
        display(box, widgets.HBox([submit, next_btn]), feedback)

    def _render_mc(self, card):
        pool = self.data.get("distractor_pool", [])
        if card["type"] == "list":
            option_pool = card["items"] + random.sample(pool, min(len(pool), 4))
            random.shuffle(option_pool)
            print(f"(Select all {len(card['items'])} correct items)")
            checkboxes = [widgets.Checkbox(description=opt, value=False) for opt in option_pool]
            box = widgets.VBox(checkboxes)
        elif card["type"] == "multiple_choice_given":
            box = widgets.RadioButtons(options=card["options"])
        else:
            options = build_mc_options(card, pool)
            box = widgets.RadioButtons(options=options)

        submit = widgets.Button(description="Submit", button_style="primary")
        feedback = widgets.Output()

        def on_submit(_):
            with feedback:
                clear_output()
                if card["type"] == "list":
                    selected = [cb.description for cb in box.children if cb.value]
                    required = set(normalize(i) for i in card["items"])
                    given = set(normalize(i) for i in selected)
                    correct = given == required
                    self._record(card, correct)
                    print("Correct!" if correct else f"Incorrect. Correct items: {', '.join(card['items'])}")
                elif card["type"] == "multiple_choice_given":
                    correct = check_mc(card, box.value)
                    self._record(card, correct)
                    print("Correct!" if correct else f"Incorrect. Correct answer: {card['answer']}")
                else:
                    target = card.get("answer") or card.get("answers", [""])[0]
                    correct = normalize(box.value) == normalize(target)
                    self._record(card, correct)
                    print("Correct!" if correct else f"Incorrect. Correct answer: {target}")
                next_btn.disabled = False

        submit.on_click(on_submit)
        next_btn = widgets.Button(description="Next", disabled=True)
        next_btn.on_click(lambda _: self.next_card())
        display(box, widgets.HBox([submit, next_btn]), feedback)

    def _record(self, card, correct):
        """In-memory only - no file write here. The session is only logged
        once the deck is fully completed (see show_summary)."""
        if correct:
            self.score += 1
        self.results.append((card["id"], correct))

    def next_card(self):
        self.idx += 1
        self.render_card()

    def show_summary(self):
        total = len(self.cards)
        pct = round(100 * self.score / total, 1) if total else 0
        print(f"Quiz complete! Score: {self.score} / {total} ({pct}%)")
        print()
        missed = [qid for qid, c in self.results if not c]
        if missed:
            print("Missed questions:", ", ".join(missed))
        print()

        # Only reaching this point means the full deck was completed -
        # partial/incomplete runs never call log_session at all.
        log_session(self.data["chapter"], self.mode, self.score, total, missed)
        print(f"Session logged to {LOG_PATH}")
