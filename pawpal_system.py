from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any, Optional
from datetime import date, timedelta
from collections import defaultdict

TIME_SLOT_ORDER = {"morning": 0, "afternoon": 1, "evening": 2}


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
    time: str = ""               # optional exact start time in "HH:MM" format, e.g. "07:30"
    recurrence_interval: str = ""  # "daily", "weekly", or "" (no recurrence)
    last_completed_date: Optional[date] = field(default=None)
    notes: str = ""
    completed: bool = False

    # ── computed helpers ──────────────────────────────────────

    @property
    def recurring(self) -> bool:
        """True when any recurrence interval is set."""
        return bool(self.recurrence_interval)

    @property
    def next_due_date(self) -> Optional[date]:
        """Date of the next occurrence, or None if the task is not recurring
        or has never been completed."""
        if not self.recurrence_interval or not self.last_completed_date:
            return None
        days = 1 if self.recurrence_interval == "daily" else 7
        return self.last_completed_date + timedelta(days=days)

    def is_due_today(self) -> bool:
        """Returns True when the task should appear in today's plan."""
        if self.recurrence_interval and self.last_completed_date:
            # recurring and already done at least once: only due again on/after next_due_date
            return date.today() >= self.next_due_date  # type: ignore[operator]
        return not self.completed

    # ── state mutations ───────────────────────────────────────

    def mark_complete(self) -> None:
        self.completed = True
        if self.recurrence_interval:
            self.last_completed_date = date.today()

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
            "time": self.time,
            "recurrence_interval": self.recurrence_interval,
            "last_completed_date": self.last_completed_date,
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
        """Build a DailyPlan by greedily scheduling tasks in priority order.

        Tasks are first sorted by ``sort_tasks_by_priority``. Each task is then
        evaluated in order:

        - Invalid tasks are skipped with a reason.
        - Tasks not due today (already completed non-recurring, or recurring
          tasks whose next_due_date is in the future) are skipped with an
          explanation that includes the next due date when available.
        - Tasks that fit within the remaining time budget are scheduled.
        - Tasks that exceed the remaining budget are skipped as "not enough time".

        Args:
            tasks: Flat list of Task objects from one or more pets.
            available_time: Total minutes the owner has today.

        Returns:
            A DailyPlan containing scheduled and unscheduled task lists,
            time totals, and plain-language explanation strings.
        """
        plan = DailyPlan(total_time_available=available_time, plan_date=date.today())
        sorted_tasks = self.sort_tasks_by_priority(tasks)

        for task in sorted_tasks:
            if not task.is_valid():
                plan.add_unscheduled_task(task, "invalid task data")
            elif not task.is_due_today():
                if task.next_due_date:
                    reason = f"next due {task.next_due_date} ({task.recurrence_interval})"
                else:
                    reason = "already completed"
                plan.add_unscheduled_task(task, reason)
            elif task.duration <= (plan.total_time_available - plan.total_time_used):
                plan.add_scheduled_task(task)
            else:
                plan.add_unscheduled_task(task, "not enough time")

        return plan

    def sort_tasks_by_priority(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by a three-level key: priority → time slot → duration.

        Sort key breakdown:
        - **priority** (1=high, 2=medium, 3=low): lower number comes first.
        - **TIME_SLOT_ORDER** (morning=0, afternoon=1, evening=2): within the
          same priority, earlier-in-the-day slots come first. Unknown slot
          values sort to the end (key 99).
        - **duration**: shortest task wins ties, keeping the schedule dense.

        Args:
            tasks: Unsorted list of Task objects.

        Returns:
            A new sorted list; the original list is not modified.
        """
        return sorted(tasks, key=lambda t: (
            t.priority,
            TIME_SLOT_ORDER.get(t.preferred_time, 99),
            t.duration,
        ))

    def sort_by_time(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks chronologically by their explicit HH:MM start time.

        The sort key is computed by a lambda that converts the ``time`` field
        (e.g. ``"07:30"``) into an ``(int, int)`` tuple ``(7, 30)``. Python
        compares tuples element-by-element, so ``(7, 30) < (8, 0)`` gives
        correct chronological ordering without any time-parsing library.

        Tasks without an explicit ``time`` field fall back to the midpoint of
        their ``preferred_time`` slot so they still sort sensibly alongside
        timed tasks:

        - morning   → ``(9, 0)``
        - afternoon → ``(13, 0)``
        - evening   → ``(18, 0)``

        Args:
            tasks: Unsorted list of Task objects.

        Returns:
            A new sorted list; the original list is not modified.
        """
        _SLOT_MIDPOINTS = {"morning": (9, 0), "afternoon": (13, 0), "evening": (18, 0)}
        return sorted(
            tasks,
            key=lambda t: (
                tuple(int(x) for x in t.time.split(":"))
                if t.time
                else _SLOT_MIDPOINTS.get(t.preferred_time, (0, 0))
            ),
        )

    def filter_tasks_that_fit(self, tasks: List[Task], available_time: int) -> List[Task]:
        """Return the subset of tasks that fit within the given time budget.

        Tasks are first sorted by priority (via ``sort_tasks_by_priority``).
        Invalid or already-completed tasks are skipped entirely. Remaining
        tasks are added greedily in priority order: each task is included only
        if its duration fits within the time still available, and the running
        budget is decremented accordingly.

        Args:
            tasks: Candidate list of Task objects.
            available_time: Total minutes available to fill.

        Returns:
            An ordered list of tasks whose combined duration does not exceed
            ``available_time``.
        """
        result: List[Task] = []
        time_left = available_time

        for task in self.sort_tasks_by_priority(tasks):
            if not task.is_valid() or task.completed:
                continue
            if task.duration <= time_left:
                result.append(task)
                time_left -= task.duration

        return result

    def _pet_name_for_task(self, task: Task) -> Optional[str]:
        """Return the name of the pet that owns this task, or None."""
        for pet in self.owner.pets:
            if any(id(t) == id(task) for t in pet.tasks):
                return pet.name
        return None

    def detect_conflicts(self, tasks: List[Task]) -> List[str]:
        """Scan tasks for scheduling problems and return human-readable warnings.

        Three independent checks are run in sequence; each appends to the same
        ``conflicts`` list so the method never raises — it only accumulates
        warning strings:

        1. **Slot overload** — a time slot's total task duration exceeds
           one-third of the owner's daily time budget (a rough proxy for
           "too much crammed into one part of the day").

        2. **Multiple high-priority tasks in the same slot** — two or more
           tasks with ``priority == 1`` share a preferred-time slot, which
           means at least one may be delayed or rushed.

        3. **Exact HH:MM collision** — two or more tasks have the same
           explicit start ``time`` (e.g. ``"08:00"``). Each warning names the
           tasks and their owning pets so the user knows exactly what clashes.

        Only valid, incomplete tasks are considered; completed and invalid
        tasks are ignored.

        Args:
            tasks: Full list of Task objects to inspect (typically from
                ``owner.get_all_tasks()``).

        Returns:
            A list of warning strings. An empty list means no conflicts were
            found. The program continues normally regardless of the result.
        """
        conflicts: List[str] = []

        # ── collect only valid, pending tasks ────────────────
        active = [t for t in tasks if t.is_valid() and not t.completed]

        # ── 1. slot-level overload ────────────────────────────
        slots: Dict[str, List[Task]] = defaultdict(list)
        for task in active:
            slots[task.preferred_time].append(task)

        slot_limit = self.owner.available_time_per_day // 3 if self.owner.available_time_per_day >= 3 else 0

        for slot, slot_tasks in slots.items():
            total = sum(t.duration for t in slot_tasks)
            if slot_limit > 0 and total > slot_limit:
                conflicts.append(
                    f"{slot.capitalize()} slot overloaded: {total} min of tasks, ~{slot_limit} min available per slot"
                )

            # ── 2. multiple high-priority tasks in the same slot ──
            high_pri = [t for t in slot_tasks if t.is_high_priority()]
            if len(high_pri) > 1:
                names = ", ".join(t.name for t in high_pri)
                conflicts.append(f"Multiple high-priority tasks in {slot}: {names}")

        # ── 3. exact HH:MM collision ─────────────────────────
        # Group tasks by their explicit start time; two or more tasks
        # sharing the same HH:MM cannot both run at that moment.
        time_groups: Dict[str, List[Task]] = defaultdict(list)
        for task in active:
            if task.time:
                time_groups[task.time].append(task)

        for time_str, clashing in time_groups.items():
            if len(clashing) > 1:
                labels = []
                for t in clashing:
                    pet_name = self._pet_name_for_task(t)
                    label = f"'{t.name}'" + (f" ({pet_name})" if pet_name else "")
                    labels.append(label)
                conflicts.append(
                    f"WARNING: time conflict at {time_str} — "
                    + " and ".join(labels)
                    + " are scheduled at the same time"
                )

        return conflicts

    def filter_tasks_by_category(self, tasks: List[Task], category: str) -> List[Task]:
        """Return all tasks whose category matches the given string (case-insensitive).

        Args:
            tasks: List of Task objects to search.
            category: Category name to match (e.g. ``"feeding"``, ``"health"``).

        Returns:
            A filtered list containing only tasks with a matching category.
            Returns an empty list if none match.
        """
        return [t for t in tasks if t.category.lower() == category.lower()]

    def filter_tasks_by_status(self, tasks: List[Task], completed: bool) -> List[Task]:
        """Return tasks filtered by completion status.

        Args:
            tasks: List of Task objects to filter.
            completed: Pass ``True`` to get only finished tasks; ``False`` for
                only pending tasks.

        Returns:
            A filtered list where every task's ``completed`` flag equals the
            ``completed`` argument.
        """
        return [t for t in tasks if t.completed == completed]

    def filter_tasks_by_pet(self, tasks: List[Task], pet_name: str) -> List[Task]:
        """Return only the tasks that belong to the named pet.

        Uses object identity (``id()``) rather than name matching so that two
        pets with tasks of the same name are never confused. The method looks up
        the pet via ``Owner.get_pet`` (case-insensitive) and builds a set of
        task ``id``s from that pet's task list, then returns every task in
        ``tasks`` whose ``id`` appears in that set.

        Args:
            tasks: Flat list of Task objects to filter (typically from
                ``owner.get_all_tasks()``).
            pet_name: Name of the pet whose tasks should be returned.

        Returns:
            Tasks owned by the named pet. Returns an empty list if the pet
            does not exist or has no tasks in the provided list.
        """
        pet = self.owner.get_pet(pet_name)
        if pet is None:
            return []
        pet_task_ids = {id(t) for t in pet.tasks}
        return [t for t in tasks if id(t) in pet_task_ids]

    def reset_recurring_tasks(self) -> List[str]:
        """Manually reset recurring tasks that are due today or overdue."""
        reset_names: List[str] = []
        for task in self.owner.get_all_tasks():
            if task.recurring and task.completed and task.is_due_today():
                task.mark_incomplete()
                reset_names.append(task.name)
        return reset_names

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
            slots: Dict[str, List[Task]] = {"morning": [], "afternoon": [], "evening": []}
            other: List[Task] = []
            for task in self.scheduled_tasks:
                if task.preferred_time in slots:
                    slots[task.preferred_time].append(task)
                else:
                    other.append(task)

            index = 1
            for slot_name, slot_tasks in slots.items():
                if slot_tasks:
                    lines.append(f"  [{slot_name.upper()}]")
                    for task in slot_tasks:
                        priority_label = {1: "high", 2: "medium", 3: "low"}.get(task.priority, str(task.priority))
                        recurring_tag = " [recurring]" if task.recurring else ""
                        time_tag = f" @{task.time}" if task.time else ""
                        lines.append(
                            f"    {index}. {task.name} - {task.duration} min"
                            f" - priority={priority_label}{time_tag}{recurring_tag}"
                        )
                        if task.notes:
                            lines.append(f"       note: {task.notes}")
                        index += 1
            for task in other:
                priority_label = {1: "high", 2: "medium", 3: "low"}.get(task.priority, str(task.priority))
                recurring_tag = " [recurring]" if task.recurring else ""
                time_tag = f" @{task.time}" if task.time else ""
                lines.append(f"  {index}. {task.name} - {task.duration} min - priority={priority_label}{time_tag}{recurring_tag}")
                index += 1
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
        total_all = self.total_time_used + sum(t.duration for t, _ in self.unscheduled_tasks)
        overload = ""
        if self.total_time_available > 0 and total_all > self.total_time_available:
            pct = int((total_all - self.total_time_available) / self.total_time_available * 100)
            overload = f" | {pct}% over capacity"
        return (
            f"{len(self.scheduled_tasks)} task(s) scheduled, "
            f"{len(self.unscheduled_tasks)} skipped, "
            f"{remaining} min free{overload}"
        )