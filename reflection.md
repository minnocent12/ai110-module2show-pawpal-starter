# PawPal+ Project Reflection

## 1. System Design


**a. Core user actions**

The three core actions a user should be able to perform in PawPal+:

1. **Enter Owner & Pet Info** — The user enters basic information about themselves and their pet, such as the owner's name, daily available time, and the pet's name, species, age, or special care notes. This information gives the system the context and constraints needed for scheduling.

2. **Manage (Add / Edit / Remove) Care Tasks** — The user can create and manage pet care tasks such as feeding, walks, medication, grooming, enrichment, or appointments. Each task should include at minimum a duration and priority, and may also include optional details like preferred time, recurrence, or notes.

3. **Generate & View Today's Daily Plan** — The user asks the system to build a daily schedule. The scheduler organizes tasks based on available time, priority, and other constraints, then displays an ordered plan along with a short explanation of why tasks were selected or prioritized.

**b. Initial design**

The initial design uses five classes organized in a clear dependency hierarchy:

- **Task** — The smallest unit of work. Holds everything needed to describe one care activity: name, category, duration, priority, optional preferred time, recurrence flag, notes, and a completed status. Responsible for validating itself and reporting whether it is high priority.

- **Pet** — Represents a specific animal being cared for. Owns a list of Task objects and is responsible for adding, removing, editing, and retrieving them. Also holds profile data (species, age, special notes) and can produce a readable summary.

- **Owner** — Represents the app user. Owns a list of Pet objects and holds the key scheduling constraint: how many minutes are available per day. Also stores preferences such as preferred walk times. Responsible for managing pets and updating time/preference settings.

- **Scheduler** — The decision-making engine. Takes an Owner and a list of Tasks, then sorts by priority, filters to what fits in the available time budget, and returns a DailyPlan. Also responsible for generating a plain-language explanation of the scheduling decisions.

- **DailyPlan** — The output object produced by the Scheduler. Holds two lists: scheduled tasks and unscheduled tasks (each paired with a skip reason). Tracks total time used versus available, stores explanation strings, and formats the result for display in the UI.

**b. Design changes**

After reviewing the initial design, several structural issues were identified that would likely surface during implementation:

1. **Orphaned `Scheduler.tasks` list** — The `Scheduler` holds its own `self.tasks` list separate from the tasks stored on each `Pet`. This creates two sources of truth that can diverge. The scheduler should derive its task list from `owner.pets` at scheduling time rather than maintaining a shadow copy.

2. **Missing task aggregation step** — `generate_daily_plan` accepts a `tasks` parameter, but nothing in the design is responsible for collecting tasks across all pets before calling it. `Owner` needs an `get_all_tasks()` method (or equivalent) to bridge this gap, otherwise the caller must know to do it manually.

3. **`DailyPlan` has no date field and no pet context** — Without a date, plans cannot be distinguished from each other. Without a reference to which pet each task belongs to, the plan output cannot display something like "Walk Buddy." Either `Task` needs a `pet_name` field, or `scheduled_tasks` should store `(Task, Pet)` tuples.

4. **`preferred_time` is stored but never used in scheduling** — `Task` has a `preferred_time` field, but neither `Scheduler.sort_tasks_by_priority` nor `filter_tasks_that_fit` accounts for it. Time-slot awareness would need to be added for this field to have any effect.

5. **`available_time_per_day` is a single integer** — Treating the day as one uninterrupted block limits scheduling realism. A future iteration could represent availability as a list of time windows instead.

6. **`Task.priority` has no defined scale** — Using a raw `int` makes `is_high_priority()` ambiguous. Replacing it with an `Enum` (e.g., `LOW=1, MEDIUM=2, HIGH=3`) would make the threshold explicit and prevent invalid values.

7. **`DailyPlan.explanations` and `Scheduler.explain_plan` overlap** — Explanation logic is split between the plan object and the scheduler. Consolidating this to one place would prevent inconsistency.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers several constraints when building a daily plan.

The most important constraint is the owner's available time per day. Every task has a duration, and the scheduler ensures that the total scheduled task time never exceeds the owner's available minutes.

The second constraint is task priority. Tasks are evaluated in priority order, with high-priority tasks considered first, followed by medium and low priority tasks. This ensures that critical pet care activities such as medication or feeding are always scheduled before less essential tasks like play or enrichment.

The scheduler also considers time preferences. Each task includes a preferred time slot (morning, afternoon, or evening), which influences sorting order when tasks share the same priority.

Additional constraints include task completion status and recurring task due dates. Completed non-recurring tasks are skipped, while recurring tasks only reappear in the plan when their `next_due_date` has arrived.

I decided that priority and time availability were the most important constraints because they directly determine whether a pet's essential care tasks will happen during the day.

**b. Tradeoffs**

**Tradeoff: exact start-time collision detection instead of overlapping-duration detection**

The conflict detector (`Scheduler.detect_conflicts`) flags a conflict only when two tasks share the *exact same* HH:MM start time (e.g., both set to `"08:00"`). It does *not* check whether a task's duration would cause it to run into the start of a later task — for example, a 30-minute task at `07:45` and a task at `08:00` would overlap in reality, but the scheduler would not warn about it.

**Why this happens:** Duration-overlap detection requires computing each task's end time (`start + duration`) and then comparing every pair of tasks to see whether any two intervals intersect. That is an O(n²) interval-overlap problem and needs validated HH:MM times on *every* task, not just some of them.

**Why the simpler check is reasonable here:** PawPal+ is a personal, low-stakes daily planner. Most pet care tasks — feeding, a walk, administering medication — do not need to be scheduled to the minute. The owner sets a `preferred_time` slot (morning / afternoon / evening) as a rough guideline, and only optionally pins a task to an exact clock time. Detecting a direct double-booking at the same minute is the most common, actionable mistake; flagging every soft overlap would produce too many warnings and make the tool feel aggressive. The tradeoff keeps the conflict logic simple, fast, and understandable while still catching the clearest scheduling mistakes.

**What would be needed to fix it:** Store a validated `time` on every task (not optional), compute `end_time = start + timedelta(minutes=duration)`, sort tasks by start time, then use a single linear scan to check whether each task's start is before the previous task's end. This is the classic interval-scheduling sweep and would be a natural next iteration.

---

## 3. AI Collaboration

**a. How you used AI**

I used VS Code Claude (Copilot Chat with `#codebase`) throughout the project to assist with several development stages.

AI was most useful for:

- **Design brainstorming** — I used Claude to review my UML design and suggest improvements to the class relationships and responsibilities.
- **Algorithm suggestions** — When implementing the scheduler, I asked Claude for ideas on useful scheduling features. This led to adding several algorithms such as time-based sorting, conflict detection, and task filtering.
- **Debugging and refactoring** — Claude helped identify mismatches between my UI and backend models (for example when the `Task` class evolved to include recurrence fields).
- **Documentation generation** — Claude was especially helpful for drafting method docstrings and improving the README feature descriptions.

The prompts that were most helpful usually included the `#codebase` tag so Claude could analyze the actual files before suggesting changes.

Example prompt:

> `#codebase Review pawpal_system.py and suggest algorithms that could make my scheduler smarter.`

This helped me identify improvements such as filtering by category, sorting by time, and detecting schedule conflicts.

**b. Judgment and verification**

One example where I did not accept an AI suggestion as-is involved conflict detection.

Claude suggested implementing full duration overlap detection, which would require calculating task end times and checking interval intersections.

Although this approach was technically correct, I decided not to implement it because:

- many tasks do not have exact start times
- it would require forcing users to enter precise times
- it would significantly increase algorithm complexity

Instead, I implemented a simpler and more appropriate rule: detecting exact HH:MM start time collisions.

I verified this decision by reviewing the scheduler's goals and testing whether the simplified rule still caught the most obvious scheduling errors.

This process reinforced that AI suggestions should be evaluated in the context of the system design, not accepted blindly.

**c. Using separate AI chat sessions**

Using separate chat sessions for different development phases helped keep the project organized.

For example:

- One chat session focused on system design and UML planning
- Another session focused on scheduler algorithm implementation
- Another session focused on testing strategies and edge cases

This separation prevented earlier design discussions from interfering with later debugging or documentation tasks. It also made it easier to ask Claude focused questions without overwhelming the context window.

**d. Being the "lead architect"**

Working with AI tools reinforced the importance of acting as the lead architect of the system.

AI is extremely useful for generating ideas, explaining algorithms, and drafting code, but it does not understand the full goals of a project unless guided carefully.

Throughout the project I learned that my role was to:

- define the architecture and responsibilities of each class
- decide which AI suggestions aligned with the project goals
- verify that generated code actually matched my design
- maintain a clear separation between the backend logic and the UI layer

The most important lesson was that AI works best as a collaborator, not a decision-maker. The developer must still guide the structure of the system and validate every major change.

---

## 4. Testing and Verification

**a. What you tested**

The test suite focuses on verifying the core behaviors of the scheduling system.

The tests cover:

- **Task completion state changes** — verifying that `mark_complete()` and `mark_incomplete()` correctly update the `completed` flag.
- **Task list management** — ensuring that adding tasks increases the pet's task list size and that duplicate task names are rejected.
- **Scheduler priority behavior** — confirming that high-priority tasks are scheduled before lower-priority tasks when time is limited.
- **Chronological sorting** — verifying that `sort_by_time()` correctly orders tasks based on HH:MM start time.
- **Recurring task logic** — ensuring that completing a recurring task correctly sets the next due date.
- **Conflict detection** — confirming that `detect_conflicts()` produces warnings when multiple tasks share the same start time.

These tests are important because they validate the core scheduling rules that determine the daily plan.

**b. Confidence**

I am fairly confident that the scheduler works correctly because the tests cover the key behaviors that influence scheduling decisions, including sorting, filtering, recurrence, and conflict detection.

However, additional tests could further increase confidence. For example:

- testing weekly recurring tasks
- testing `reset_recurring_tasks()` behavior
- testing extreme cases such as many tasks exceeding available time
- testing interactions between multiple pets with overlapping tasks

Adding UI-level integration tests would also improve confidence in the full application.

---

## 5. Reflection

**a. What went well**

The part of the project I am most satisfied with is the scheduler design.

The system evolved from a simple priority sorter into a more intelligent planner that supports time-based sorting, recurring tasks, conflict detection, and multiple filtering options.

I am also pleased with how clearly the responsibilities of each class are separated. `Owner`, `Pet`, `Task`, `Scheduler`, and `DailyPlan` each have well-defined roles, which made the system easier to extend.

**b. What you would improve**

If I had another iteration, I would improve the scheduling model by supporting true time-window scheduling.

Currently, the day is treated as a single block of available minutes. A more realistic system would allow the owner to define multiple time windows (for example morning before work, lunch break, evening), and the scheduler would assign tasks into those windows.

I would also consider implementing duration overlap detection and allowing tasks to automatically shift within their preferred time slots.

**c. Key takeaway**

One of the most important lessons from this project was learning how to design systems collaboratively with AI while maintaining architectural control.

AI tools like Claude can accelerate development by generating ideas, explaining algorithms, and helping debug issues. However, the developer must still act as the system architect — defining class responsibilities, validating suggestions, and ensuring that the final implementation remains clean and coherent.

This experience reinforced that good software design still depends on human judgment, even when powerful AI tools are involved.
