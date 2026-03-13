from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any

class Owner:
    def __init__(self, name: str, available_time_per_day: int, preferences: Dict[str, Any]):
        self.name: str = name
        self.available_time_per_day: int = available_time_per_day
        self.preferences: Dict[str, Any] = preferences
        self.pets: List[Pet] = []

    def add_pet(self, pet: 'Pet'):
        pass

    def remove_pet(self, pet_name: str):
        pass

    def get_pet(self, pet_name: str) -> 'Pet':
        pass

    def update_available_time(self, minutes: int):
        pass

    def update_preferences(self, preferences: Dict[str, Any]):
        pass


@dataclass
class Task:
    name: str
    category: str
    duration: int
    priority: int
    preferred_time: str
    recurring: bool
    notes: str
    completed: bool

    def mark_complete(self):
        pass

    def mark_incomplete(self):
        pass

    def update_details(self, **kwargs):
        pass

    def is_high_priority(self) -> bool:
        pass

    def is_valid(self) -> bool:
        pass

    def to_dict(self) -> Dict[str, Any]:
        pass


@dataclass
class Pet:
    name: str
    species: str
    age: int
    notes: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task):
        pass

    def remove_task(self, task_name: str):
        pass

    def edit_task(self, task_name: str, **kwargs):
        pass

    def get_tasks(self) -> List[Task]:
        pass

    def summary(self) -> str:
        pass


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner: Owner = owner
        self.tasks: List[Task] = []

    def generate_daily_plan(self, tasks: List[Task], available_time: int) -> 'DailyPlan':
        pass

    def sort_tasks_by_priority(self, tasks: List[Task]) -> List[Task]:
        pass

    def filter_tasks_that_fit(self, tasks: List[Task], available_time: int) -> List[Task]:
        pass

    def explain_plan(self, plan: 'DailyPlan') -> str:
        pass


class DailyPlan:
    def __init__(self, total_time_available: int):
        self.scheduled_tasks: List[Task] = []
        self.unscheduled_tasks: List[Tuple[Task, str]] = []
        self.total_time_used: int = 0
        self.total_time_available: int = total_time_available
        self.explanations: List[str] = []

    def add_scheduled_task(self, task: Task):
        pass

    def add_unscheduled_task(self, task: Task, reason: str):
        pass

    def display_plan(self) -> str:
        pass

    def get_summary(self) -> str:
        pass