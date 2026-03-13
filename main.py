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
    recurring_str = input("  Recurring? (y/n) [default n]: ").strip().lower()
    recurring = recurring_str == "y"
    notes = input("  Notes (optional): ").strip()

    return Task(
        name=name,
        category=category,
        duration=duration,
        priority=priority,
        preferred_time=preferred_time,
        recurring=recurring,
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
  7. Quit
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
                    print(f"    {i}. {task.name} ({status})")

                try:
                    index = int(input("  Task number to mark complete: ").strip()) - 1
                    if 0 <= index < len(pet.tasks):
                        pet.tasks[index].mark_complete()
                        print(f"  Marked '{pet.tasks[index].name}' as complete.")
                    else:
                        print("  Invalid task number.")
                except ValueError:
                    print("  Please enter a valid number.")

        elif choice == "5":
            all_tasks = owner.get_all_tasks()
            if not all_tasks:
                print("  No tasks found. Add pets and tasks first.")
            else:
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
            print("Goodbye!")
            break

        else:
            print("  Unknown option.")


if __name__ == "__main__":
    main()