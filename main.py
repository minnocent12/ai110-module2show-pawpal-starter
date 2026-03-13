import sys
from typing import Optional
from pawpal_system import Owner, Pet, Task, Scheduler


def _priority_label(priority: int) -> str:
    return {1: "high", 2: "medium", 3: "low"}.get(priority, str(priority))


def _prompt_task() -> Task:
    name = input("  Task name: ").strip()
    category = input("  Category (e.g. exercise, feeding, grooming): ").strip() or "general"

    while True:
        try:
            duration = int(input("  Duration (minutes): ").strip())
            if duration > 0:
                break
            print("  Duration must be greater than 0.")
        except ValueError:
            print("  Please enter a valid number.")

    while True:
        try:
            priority_str = input("  Priority — 1=high, 2=medium, 3=low [default 2]: ").strip() or "2"
            priority = int(priority_str)
            if priority in (1, 2, 3):
                break
            print("  Priority must be 1, 2, or 3.")
        except ValueError:
            print("  Please enter a valid number.")

    preferred_time = input("  Preferred time (morning/afternoon/evening) [default morning]: ").strip() or "morning"

    task_time = ""
    while True:
        raw = input("  Exact start time in HH:MM (optional, press Enter to skip): ").strip()
        if not raw:
            break
        parts = raw.split(":")
        if (
            len(parts) == 2
            and parts[0].isdigit()
            and parts[1].isdigit()
            and 0 <= int(parts[0]) <= 23
            and 0 <= int(parts[1]) <= 59
        ):
            task_time = f"{int(parts[0]):02d}:{int(parts[1]):02d}"
            break
        print("  Please enter a valid time like 07:30 or 14:00.")

    recurrence_interval = ""
    while True:
        raw = input("  Recurrence — none / daily / weekly [default none]: ").strip().lower() or "none"
        if raw in ("none", "daily", "weekly"):
            recurrence_interval = "" if raw == "none" else raw
            break
        print("  Please enter none, daily, or weekly.")

    notes = input("  Notes (optional): ").strip()

    return Task(
        name=name,
        category=category,
        duration=duration,
        priority=priority,
        preferred_time=preferred_time,
        time=task_time,
        recurrence_interval=recurrence_interval,
        notes=notes,
    )


def _list_pets(owner: Owner) -> None:
    if not owner.pets:
        print("  No pets added yet.")
        return

    for pet in owner.pets:
        print(f"  {pet.summary()}")


def _select_pet(owner: Owner) -> Optional[Pet]:
    if not owner.pets:
        print("  No pets yet.")
        return None

    for i, pet in enumerate(owner.pets, 1):
        print(f"  {i}. {pet.name}")

    try:
        index = int(input("  Select pet number: ").strip()) - 1
        if 0 <= index < len(owner.pets):
            return owner.pets[index]
    except ValueError:
        pass

    print("  Invalid selection.")
    return None


def main() -> None:
    print("=== PawPal+ CLI ===")
    owner_name = input("Your name: ").strip() or "Owner"

    while True:
        try:
            time_str = input("Available time today (minutes) [default 60]: ").strip() or "60"
            available_minutes = int(time_str)
            if available_minutes >= 0:
                break
            print("Please enter 0 or more minutes.")
        except ValueError:
            print("Please enter a valid number.")

    owner = Owner(
        name=owner_name,
        available_time_per_day=available_minutes,
        preferences={},
    )
    scheduler = Scheduler(owner)

    menu = """
Actions:
  1. Add pet
  2. Add task to a pet
  3. List pets and tasks
  4. Mark task complete
  5. Generate daily plan
  6. Update available time
  7. Reset recurring tasks
  8. Filter tasks by category
  9. Quit
"""

    while True:
        print(menu)
        choice = input("Choose an action: ").strip()

        if choice == "1":
            pet_name = input("  Pet name: ").strip()
            species = input("  Species: ").strip()

            try:
                age = int(input("  Age (years): ").strip())
            except ValueError:
                print("  Invalid age.")
                continue

            notes = input("  Notes (optional): ").strip()
            added = owner.add_pet(Pet(name=pet_name, species=species, age=age, notes=notes))

            if added:
                print(f"  Added {pet_name}.")
            else:
                print(f"  Pet '{pet_name}' already exists.")

        elif choice == "2":
            pet = _select_pet(owner)
            if pet:
                print(f"  Adding task for {pet.name}:")
                task = _prompt_task()
                if pet.add_task(task):
                    print(f"  Task '{task.name}' added.")
                else:
                    print("  Task could not be added. It may be invalid or already exist.")

        elif choice == "3":
            _list_pets(owner)
            for pet in owner.pets:
                if pet.tasks:
                    print(f"\n  {pet.name}'s tasks:")
                    for task in pet.tasks:
                        status = "done" if task.completed else "pending"
                        print(
                            f"    [{status}] {task.name} - {task.duration} min - "
                            f"priority={_priority_label(task.priority)} - @{task.preferred_time}"
                        )

        elif choice == "4":
            pet = _select_pet(owner)
            if pet and pet.tasks:
                print(f"  Tasks for {pet.name}:")
                for i, task in enumerate(pet.tasks, 1):
                    status = "done" if task.completed else "pending"
                    recurring_tag = " [recurring]" if task.recurring else ""
                    print(f"    {i}. {task.name} ({status}){recurring_tag}")

                try:
                    index = int(input("  Task number to mark complete: ").strip()) - 1
                    if 0 <= index < len(pet.tasks):
                        task = pet.tasks[index]
                        task.mark_complete()
                        print(f"  Marked '{task.name}' as complete.")
                        if task.recurring and task.next_due_date:
                            print(f"  Next occurrence: {task.next_due_date} ({task.recurrence_interval})")
                    else:
                        print("  Invalid task number.")
                except ValueError:
                    print("  Please enter a valid number.")

        elif choice == "5":
            all_tasks = owner.get_all_tasks()
            if not all_tasks:
                print("  No tasks found. Add pets and tasks first.")
            else:
                conflicts = scheduler.detect_conflicts(all_tasks)
                if conflicts:
                    print("\n  WARNINGS:")
                    for c in conflicts:
                        print(f"    ! {c}")
                plan = scheduler.generate_daily_plan(all_tasks, owner.available_time_per_day)
                print("\n" + plan.display_plan())
                print("\nSummary:", plan.get_summary())
                print("\nDetailed explanation:")
                print(scheduler.explain_plan(plan))

        elif choice == "6":
            try:
                minutes = int(input("  New available time (minutes): ").strip())
                if minutes < 0:
                    print("  Time cannot be negative.")
                    continue
                owner.update_available_time(minutes)
                print(f"  Updated to {minutes} min.")
            except ValueError:
                print("  Please enter a valid number.")

        elif choice == "7":
            reset_names = scheduler.reset_recurring_tasks()
            if reset_names:
                print(f"  Reset {len(reset_names)} recurring task(s): {', '.join(reset_names)}")
            else:
                print("  No completed recurring tasks to reset.")

        elif choice == "8":
            all_tasks = owner.get_all_tasks()
            if not all_tasks:
                print("  No tasks found.")
            else:
                categories = sorted({t.category for t in all_tasks})
                print("  Available categories:", ", ".join(categories))
                cat = input("  Filter by category: ").strip()
                filtered = scheduler.filter_tasks_by_category(all_tasks, cat)
                if not filtered:
                    print(f"  No tasks in category '{cat}'.")
                else:
                    print(f"\n  Tasks in '{cat}':")
                    for task in filtered:
                        status = "done" if task.completed else "pending"
                        recurring_tag = " [recurring]" if task.recurring else ""
                        print(
                            f"    [{status}] {task.name} - {task.duration} min"
                            f" - priority={_priority_label(task.priority)}"
                            f" - @{task.preferred_time}{recurring_tag}"
                        )

        elif choice == "9":
            print("Goodbye!")
            break

        else:
            print("  Unknown option.")


def _fmt(task: Task) -> str:
    status = "done" if task.completed else "pending"
    time_tag = f" @{task.time}" if task.time else ""
    recur_tag = f" [{task.recurrence_interval}]" if task.recurrence_interval else ""
    due_tag = f" next={task.next_due_date}" if task.next_due_date else ""
    return (
        f"  [{status}] {task.name:<20} {task.duration:>3} min"
        f"  priority={_priority_label(task.priority)}"
        f"  slot={task.preferred_time}{time_tag}{recur_tag}{due_tag}"
    )


def demo_run() -> None:
    print("=" * 60)
    print("  PawPal+ DEMO — sorting & filtering")
    print("=" * 60)

    # ── setup ──────────────────────────────────────────────────
    owner = Owner(name="Alex", available_time_per_day=120, preferences={})
    scheduler = Scheduler(owner)

    buddy = Pet(name="Buddy", species="dog", age=3, notes="")
    luna  = Pet(name="Luna",  species="cat", age=5, notes="")
    owner.add_pet(buddy)
    owner.add_pet(luna)

    # Tasks added INTENTIONALLY out of order
    # (scrambled across pets, slots, and start times)
    buddy.add_task(Task("Evening Walk",   "exercise", 30, 2, "evening",   time="19:00", recurrence_interval="daily"))
    luna.add_task( Task("Litter Clean",   "grooming", 15, 2, "afternoon", time="13:00", recurrence_interval="weekly"))
    luna.add_task( Task("Hairball Med",   "health",    5, 1, "morning",   time="09:30", recurrence_interval="daily"))
    buddy.add_task(Task("Morning Meds",   "health",    5, 1, "morning",   time="07:15", recurrence_interval="daily"))
    buddy.add_task(Task("Breakfast Feed", "feeding",  10, 1, "morning",   time="08:00", recurrence_interval="daily"))
    buddy.add_task(Task("Afternoon Play", "exercise", 20, 3, "afternoon", time="14:30"))

    all_tasks = owner.get_all_tasks()

    # ── 1. as-added order ──────────────────────────────────────
    print("\n--- As added (original order) ---")
    for t in all_tasks:
        print(_fmt(t))

    # ── 2. sorted by HH:MM time ───────────────────────────────
    print("\n--- Sorted by start time (sort_by_time) ---")
    for t in scheduler.sort_by_time(all_tasks):
        print(_fmt(t))

    # ── 3. sorted by priority + slot ──────────────────────────
    print("\n--- Sorted by priority + slot (sort_tasks_by_priority) ---")
    for t in scheduler.sort_tasks_by_priority(all_tasks):
        print(_fmt(t))

    # ── 4. filter: pending only ───────────────────────────────
    print("\n--- Filter: pending tasks only ---")
    pending = scheduler.filter_tasks_by_status(all_tasks, completed=False)
    for t in pending:
        print(_fmt(t))

    # ── 5. mark two tasks complete, then filter completed ─────
    buddy.tasks[1].mark_complete()   # Morning Meds
    luna.tasks[0].mark_complete()    # Litter Clean
    print("\n--- After marking 'Morning Meds' and 'Litter Clean' done ---")
    print("    Filter: completed tasks only")
    for t in scheduler.filter_tasks_by_status(all_tasks, completed=True):
        print(_fmt(t))
    print("    Filter: pending tasks only")
    for t in scheduler.filter_tasks_by_status(all_tasks, completed=False):
        print(_fmt(t))

    # ── 6. filter by pet ──────────────────────────────────────
    print("\n--- Filter: Buddy's tasks only (filter_tasks_by_pet) ---")
    for t in scheduler.filter_tasks_by_pet(all_tasks, "Buddy"):
        print(_fmt(t))

    print("\n--- Filter: Luna's tasks only (filter_tasks_by_pet) ---")
    for t in scheduler.filter_tasks_by_pet(all_tasks, "Luna"):
        print(_fmt(t))

    # ── 7. conflict detection ─────────────────────────────────
    print("\n--- Conflict detection (detect_conflicts) ---")
    print("  Adding two more tasks that start at the same time (08:00):")

    # Buddy: vet call at 08:00 — clashes with Breakfast Feed (also 08:00)
    buddy.add_task(Task("Vet Call", "health", 20, 1, "morning", time="08:00"))
    # Luna: pill at 08:00 — three-way clash
    luna.add_task(Task("Morning Pill", "health", 5, 1, "morning", time="08:00"))

    all_tasks = owner.get_all_tasks()   # refresh after new tasks
    conflicts = scheduler.detect_conflicts(all_tasks)
    if conflicts:
        for warning in conflicts:
            print(f"  ! {warning}")
    else:
        print("  (no conflicts found)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_run()
    else:
        main()