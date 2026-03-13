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

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
