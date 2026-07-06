# IAAO-102

Study materials and a self-built flashcard/quiz app for IAAO Course 102
(*Income Approach to Valuation*), self-paced online course.

## Repo contents

```
IAAO-102/
├── Quiz.ipynb                   # Run this - the interactive quiz notebook
├── quiz_engine.py               # All quiz logic (grading, MC generation, logging)
├── data/
│   ├── ch1_flashcards.json      # Chapter 1 review questions (20)
│   ├── ch2_flashcards.json      # Chapter 2 review questions (25)
│   └── attempts_log.csv         # Auto-generated quiz session history (see below)
├── Chapter1_StudyGuide.md       # Chapter 1 concepts, definitions, formulas
├── Chapter2_StudyGuide.md       # Chapter 2 concepts, definitions, formulas
├── 102_SRM.pdf                  # Course SRM (Self-paced Reading Material)
├── 102_SRM_solutions.pdf        # Official SRM review question solutions
└── README.md
```

## Setup

Requires Python 3 with Jupyter, `ipywidgets`, and `pandas`:

```bash
pip install jupyter ipywidgets pandas
```

Then, from the repo root:

```bash
jupyter notebook Quiz.ipynb
```

Run all cells top to bottom.

## How the quiz works

`Quiz.ipynb` is intentionally thin — it only imports from `quiz_engine.py` and
runs `QuizApp()`. All grading logic, multiple-choice generation, and logging
live in that one module.

**Two modes:**
- **Recall** — you type your answer (or one item per line for list-type
  questions), matching how you'd study manually.
- **Multiple Choice** — auto-generated options pulled from each chapter's
  `distractor_pool`, closer to the real exam format.

**Grading is strict, all-or-nothing.** List-type questions (e.g. "list four
types of mortgages...") require every item to be present to count as correct
— no partial credit. This matches how the actual exam works (multiple choice,
exact terminology), even though the practice format here is more flexible.

## Logging (`data/attempts_log.csv`)

**One row per completed session, not per question.** A session is only
logged once you've answered every card in a chapter's deck — the log write
happens in `show_summary()`, which only runs when the deck is fully
exhausted.

**Partial/incomplete runs are discarded entirely.** If you close the
notebook, restart the kernel, or stop partway through a deck, nothing gets
written for that attempt. There's no "incomplete" flag or partial record —
the run simply doesn't count.

Log schema:

| column | meaning |
|---|---|
| `timestamp` | when the session was completed |
| `chapter` | which chapter's flashcard set |
| `mode` | `recall` or `mc` |
| `score` | number correct |
| `total` | number of questions in the deck |
| `pct` | score as a percentage |
| `missed_question_ids` | semicolon-separated list of question IDs missed |

The notebook's progress-history cell reads this file back and shows your
score trend over time, plus your most frequently missed questions across all
logged sessions.

## Adding a new chapter

Drop a new `chN_flashcards.json` file into `data/`, following the schema
used by `ch1_flashcards.json` / `ch2_flashcards.json` (a `chapter` number,
a `title`, a `cards` array with `id`/`type`/`prompt`/`answer` or
`items`/`answers`, and an optional `distractor_pool` for multiple choice).
No changes to `quiz_engine.py` or the notebook are needed — chapters are
auto-detected from the `data/` folder.

## Study guides and Priority Review sections

`Chapter1_StudyGuide.md` and `Chapter2_StudyGuide.md` cover the underlying
concepts, definitions, and formulas for each chapter — broader than just the
review questions, meant for actually learning the material rather than only
drilling it.

Each guide also has a **Priority Review** section near the top, tagging
every review question 🔴 High / 🟡 Medium / 🟢 Low / ⚪ Not Yet Attempted,
based on historical performance in `attempts_log.csv` at the time the
section was generated.

**Important: this section is a static snapshot, not a live view.** It was
generated once from whatever was in the log at that time and written
directly into the markdown file as plain text — it has no ongoing
connection back to the CSV. As more quiz sessions get logged and your recall
improves, the tags will **not** update on their own. Regenerating them is a
manual step (currently done by re-running the tiering logic against the
latest log and re-inserting the section) — not something that happens
automatically on a schedule or on notebook run.

## Current status

- Chapter 1 and Chapter 2 review questions and study guides are complete.
- `data/attempts_log.csv` currently contains one seeded session (a manual
  Chapter 1 attempt, scored 9/20 under strict grading, predating the quiz
  app itself).
- Priority Review tags reflect that single data point and will read as
  fairly binary (missed-once = High) until more sessions accumulate.