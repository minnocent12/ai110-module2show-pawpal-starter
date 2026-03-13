from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any, Optional
from datetime import date


class Owner:
    def __init__(self, name: str, available_time_per_day: int, preferences: Dict[str, Any]):
        self.name: str = name
        self.available_time_per_day: int = available_time_per_day
        self.preferences: Dict[str, Any] = preferences
        self.pets: List['Pet'] = []

    def add_pet(self, pet: 'Pet') -> bool:
        if self.get_pet(pet.name) is not None:
            return False
        self.pets.append(pet)
        return True

    def remove_pet(self, pet_name: str) -> bool:
        original_count = len(self.pets)
        self.pets = [p for p in self.pets if p.name.lower() != pet_name.lower()]
        return len(self.pets) < original_count

    def get_pet(self, pet_name: str) -> Optional['Pet']:
        for pet in self.pets:
            if pet.name.lower() == pet_name.lower():
                return pet
        return None

    def update_available_time(self, minutes: int) -> None:
        if minutes >= 0:
            self.available_time_per_day = minutes

    def update_preferences(self, preferences: Dict[str, Any]) -> None:
        self.preferences.update(preferences)

    def get_all_tasks(self) -> List['Task']:
        all_tasks: List['Task'] = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks


@dataclass
class Task:
    name: str
    category: str
    duration: int
    priority: int  # 1 = highest, 3 = lowest
    preferred_time: str = "morning"
    recurring: bool = False
    notes: str = ""
    completed: bool = False

    def mark_complete(self) -> None:
        self.completed = True

    def mark_incomplete(self) -> None:
        self.completed = False

    def update_details(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def is_high_priority(self) -> bool:
        return self.priority == 1

    def is_valid(self) -> bool:
        return (
            bool(self.name.strip())
            and bool(self.category.strip())
            and self.duration > 0
            and self.priority in (1, 2, 3)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "duration": self.duration,
            "priority": self.priority,
            "preferred_time": self.preferred_time,
            "recurring": self.recurring,
            "notes": self.notes,
            "completed": self.completed,
        }


@dataclass
class Pet:
    name: str
    species: str
    age: int
    notes: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> bool:
        if not task.is_valid():
            return False

        for existing_task in self.tasks:
            if existing_task.name.lower() == task.name.lower():
                return False

        self.tasks.append(task)
        return True

    def remove_task(self, task_name: str) -> bool:
        original_count = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.name.lower() != task_name.lower()]
        return len(self.tasks) < original_count

    def edit_task(self, task_name: str, **kwargs) -> bool:
        for task in self.tasks:
            if task.name.lower() == task_name.lower():
                old_values = task.to_dict()
                task.update_details(**kwargs)

                if not task.is_valid():
                    task.update_details(**old_values)
                    return False
                return True
        return False

    def get_tasks(self) -> List[Task]:
        return self.tasks

    def summary(self) -> str:
        total = len(self.tasks)
        completed_count = sum(1 for t in self.tasks if t.completed)
        remaining_minutes = sum(t.duration for t in self.tasks if not t.completed)
        return (
            f"{self.name} ({self.species}, {self.age}y) — "
            f"{total} task(s), {completed_count} completed, {remaining_minutes} min remaining"
        )


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner: Owner = owner

    def generate_daily_plan(self, tasks: List[Task], available_time: int) -> 'DailyPlan':
        plan = DailyPlan(total_time_available=available_time, plan_date=date.today())
        sorted_tasks = self.sort_tasks_by_priority(tasks)

        for task in sorted_tasks:
            if not task.is_valid():
                plan.add_unscheduled_task(task, "invalid task data")
            elif task.completed:
                plan.add_unscheduled_task(task, "already completed")
            elif task.duration <= (plan.total_time_available - plan.total_time_used):
                plan.add_scheduled_task(task)
            else:
                plan.add_unscheduled_task(task, "not enough time")

        return plan

    def sort_tasks_by_priority(self, tasks: List[Task]) -> List[Task]:
        return sorted(tasks, key=lambda t: (t.priority, t.duration))

    def filter_tasks_that_fit(self, tasks: List[Task], available_time: int) -> List[Task]:
        result: List[Task] = []
        time_left = available_time

        for task in self.sort_tasks_by_priority(tasks):
            if not task.is_valid() or task.completed:
                continue
            if task.duration <= time_left:
                result.append(task)
                time_left -= task.duration

        return result

    def explain_plan(self, plan: 'DailyPlan') -> str:
        lines = [f"Plan for {plan.plan_date} | {plan.total_time_available} min available", ""]

        lines.append("Explanations:")
        if plan.explanations:
            for explanation in plan.explanations:
                lines.append(f"  - {explanation}")
        else:
            lines.append("  (no explanations available)")

        lines.append("")
        lines.append(f"Time used: {plan.total_time_used}/{plan.total_time_available} min")
        return "\n".join(lines)


class DailyPlan:
    def __init__(self, total_time_available: int, plan_date: Optional[date] = None):
        self.plan_date: date = plan_date or date.today()
        self.scheduled_tasks: List[Task] = []
        self.unscheduled_tasks: List[Tuple[Task, str]] = []
        self.total_time_used: int = 0
        self.total_time_available: int = total_time_available
        self.explanations: List[str] = []

    def add_scheduled_task(self, task: Task) -> None:
        self.scheduled_tasks.append(task)
        self.total_time_used += task.duration
        priority_label = {1: "high", 2: "medium", 3: "low"}.get(task.priority, str(task.priority))
        self.explanations.append(
            f"Scheduled '{task.name}' because it is {priority_label} priority and fits in the remaining time."
        )

    def add_unscheduled_task(self, task: Task, reason: str) -> None:
        self.unscheduled_tasks.append((task, reason))
        self.explanations.append(f"Skipped '{task.name}' because {reason}.")

    def display_plan(self) -> str:
        lines = [
            f"=== Daily Plan — {self.plan_date} ===",
            f"Time available: {self.total_time_available} min | Time used: {self.total_time_used} min",
            "",
            "SCHEDULED TASKS:",
        ]

        if self.scheduled_tasks:
            for index, task in enumerate(self.scheduled_tasks, 1):
                priority_label = {1: "high", 2: "medium", 3: "low"}.get(task.priority, str(task.priority))
                lines.append(
                    f"  {index}. [{task.preferred_time}] {task.name} "
                    f"- {task.duration} min - priority={priority_label}"
                )
                if task.notes:
                    lines.append(f"     note: {task.notes}")
        else:
            lines.append("  (no tasks scheduled)")

        lines.append("")
        lines.append("NOT SCHEDULED:")
        if self.unscheduled_tasks:
            for task, reason in self.unscheduled_tasks:
                lines.append(f"  - {task.name} ({reason})")
        else:
            lines.append("  (all tasks fit)")

        return "\n".join(lines)

    def get_summary(self) -> str:
        remaining = self.total_time_available - self.total_time_used
        return (
            f"{len(self.scheduled_tasks)} task(s) scheduled, "
            f"{len(self.unscheduled_tasks)} skipped, "
            f"{remaining} min free"
        )