import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler


def make_task(name="Walk", duration=20, priority=1):
    return Task(name=name, category="exercise", duration=duration, priority=priority)


def make_pet():
    return Pet(name="Mochi", species="dog", age=3, notes="")


# --- Test 1: mark_complete() changes completed to True ---
def test_mark_complete_sets_completed():
    task = make_task()
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


# --- Test 2: mark_incomplete() resets completed to False ---
def test_mark_incomplete_resets_completed():
    task = make_task()
    task.mark_complete()
    task.mark_incomplete()
    assert task.completed is False


# --- Test 3: adding a task increases the pet's task count ---
def test_add_task_increases_task_count():
    pet = make_pet()
    assert len(pet.get_tasks()) == 0
    pet.add_task(make_task("Walk", 20, 1))
    assert len(pet.get_tasks()) == 1
    pet.add_task(make_task("Feeding", 5, 1))
    assert len(pet.get_tasks()) == 2


# --- Test 4: adding a duplicate task does not increase the count ---
def test_add_duplicate_task_rejected():
    pet = make_pet()
    task = make_task()
    pet.add_task(task)
    result = pet.add_task(make_task())   # same name
    assert result is False
    assert len(pet.get_tasks()) == 1


# --- Test 5: scheduler skips completed tasks in the daily plan ---
def test_scheduler_skips_completed_tasks():
    owner = Owner("Jordan", 60, {})
    pet = make_pet()
    owner.add_pet(pet)

    task = make_task("Walk", 20, 1)
    task.mark_complete()
    pet.add_task(task)
    pet.add_task(make_task("Feeding", 5, 1))

    scheduler = Scheduler(owner)
    plan = scheduler.generate_daily_plan(owner.get_all_tasks(), owner.available_time_per_day)

    scheduled_names = [t.name for t in plan.scheduled_tasks]
    assert "Walk" not in scheduled_names
    assert "Feeding" in scheduled_names
    
# --- Test 6: scheduler prioritizes higher-priority tasks within limited time ---
def test_scheduler_respects_priority_with_limited_time():
    owner = Owner("Jordan", 25, {})
    pet = make_pet()
    owner.add_pet(pet)

    pet.add_task(make_task("High Priority Walk", 20, 1))   # high priority
    pet.add_task(make_task("Medium Grooming", 10, 2))      # medium priority
    pet.add_task(make_task("Low Playtime", 5, 3))          # low priority

    scheduler = Scheduler(owner)
    plan = scheduler.generate_daily_plan(owner.get_all_tasks(), owner.available_time_per_day)

    scheduled_names = [task.name for task in plan.scheduled_tasks]
    skipped_names = [task.name for task, _ in plan.unscheduled_tasks]

    assert "High Priority Walk" in scheduled_names
    assert "Low Playtime" in scheduled_names
    assert "Medium Grooming" in skipped_names
    assert plan.total_time_used == 25


# --- Test 7: sort_by_time returns tasks in chronological HH:MM order ---
def test_sort_by_time_returns_chronological_order():
    owner = Owner("Jordan", 120, {})
    scheduler = Scheduler(owner)

    evening  = Task(name="Evening Walk",   category="exercise", duration=20, priority=2, time="18:00")
    morning  = Task(name="Morning Feed",   category="feeding",  duration=10, priority=1, time="07:30")
    midday   = Task(name="Midday Meds",    category="health",   duration=5,  priority=1, time="12:15")

    sorted_tasks = scheduler.sort_by_time([evening, morning, midday])

    assert [t.name for t in sorted_tasks] == [
        "Morning Feed",
        "Midday Meds",
        "Evening Walk",
    ]


# --- Test 8: marking a daily task complete schedules it for the next day ---
def test_daily_recurring_task_due_tomorrow_after_completion():
    task = Task(
        name="Daily Walk",
        category="exercise",
        duration=30,
        priority=1,
        recurrence_interval="daily",
    )

    task.mark_complete()

    # completed flag is set and last_completed_date recorded
    assert task.completed is True
    assert task.last_completed_date == date.today()

    # next occurrence is exactly one day away
    assert task.next_due_date == date.today() + timedelta(days=1)

    # task must NOT appear in today's plan (it was just done)
    assert task.is_due_today() is False


# --- Test 9: detect_conflicts flags tasks with the same explicit start time ---
def test_detect_conflicts_flags_duplicate_start_times():
    owner = Owner("Jordan", 120, {})
    pet = Pet(name="Mochi", species="dog", age=3, notes="")
    owner.add_pet(pet)

    # Two different tasks assigned the same HH:MM slot
    task_a = Task(name="Morning Feed",  category="feeding",  duration=10, priority=1, time="08:00")
    task_b = Task(name="Morning Meds",  category="health",   duration=5,  priority=1, time="08:00")
    pet.add_task(task_a)
    pet.add_task(task_b)

    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts(owner.get_all_tasks())

    # At least one conflict message must mention the clashing time
    assert any("08:00" in msg for msg in conflicts), (
        f"Expected a conflict at 08:00 but got: {conflicts}"
    )