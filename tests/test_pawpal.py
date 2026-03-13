import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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