# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

Phase 3 added a set of algorithms that make the scheduler more intelligent and the daily plan more useful.

### Sorting

| Method | What it does |
|---|---|
| `sort_tasks_by_priority` | Sorts by priority (1→3), then time slot (morning→evening), then shortest duration first. Ensures high-priority morning tasks are always evaluated first. |
| `sort_by_time` | Sorts tasks chronologically by their optional HH:MM start time. Uses a lambda that converts `"07:30"` → `(7, 30)` so Python's tuple comparison gives correct clock order. Tasks without an explicit time fall back to their slot's midpoint. |

### Filtering

| Method | What it does |
|---|---|
| `filter_tasks_by_status(completed=True/False)` | Returns only done or only pending tasks from any list. |
| `filter_tasks_by_pet(pet_name)` | Returns tasks belonging to one specific pet, using object identity so same-named tasks across different pets are never confused. |
| `filter_tasks_by_category(category)` | Returns tasks matching a category string (case-insensitive), e.g. `"health"`, `"exercise"`. |

### Recurring tasks

Tasks now have a `recurrence_interval` field (`"daily"` or `"weekly"`). When `mark_complete()` is called, `last_completed_date` is set automatically. The `next_due_date` property computes the next occurrence using `timedelta`, and `is_due_today()` determines whether the task re-enters the plan — no manual reset required.

### Conflict detection

`detect_conflicts` runs three lightweight checks and returns warning strings rather than raising exceptions:

1. **Slot overload** — a slot's total task time exceeds one-third of the daily budget.
2. **Multiple high-priority tasks in one slot** — two or more `priority=1` tasks compete for the same time of day.
3. **Exact HH:MM collision** — two or more tasks share the same explicit start time. Warnings name each task and its owning pet.

### Running the demo

```bash
python3 main.py --demo
```

This runs a scripted scenario that adds tasks out of order across two pets, then prints each sorting and filtering result, and triggers a three-way time conflict at `08:00` to demonstrate the warning output.

---

## Getting started

### Setup

```bash
python -m venv .venv

or

python3 -m venv .venv

source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
