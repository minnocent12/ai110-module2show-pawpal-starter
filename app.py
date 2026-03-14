import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to PawPal+, the smart pet care planning assistant.

Use the app to add pets, create care tasks, review smart scheduling insights,
and generate a daily plan.
"""
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None
if "scheduler" not in st.session_state:
    st.session_state.scheduler = None
if "plan" not in st.session_state:
    st.session_state.plan = None

# ---------------------------------------------------------------------------
# Section 1: Owner setup
# ---------------------------------------------------------------------------
st.subheader("Owner Setup")

with st.form("owner_form"):
    owner_name = st.text_input("Your name", value="Jordan")
    available_time = st.number_input(
        "Available time today (minutes)", min_value=0, max_value=480, value=60
    )
    submitted = st.form_submit_button("Save owner")

if submitted:
    existing_pets = []
    if st.session_state.owner is not None:
        existing_pets = st.session_state.owner.pets

    st.session_state.owner = Owner(
        name=owner_name,
        available_time_per_day=int(available_time),
        preferences={},
    )
    st.session_state.owner.pets = existing_pets
    st.session_state.scheduler = Scheduler(st.session_state.owner)
    st.session_state.plan = None
    st.success(f"Owner '{owner_name}' saved with {available_time} min available.")

if st.session_state.owner is None:
    st.info("Fill in your name and available time above, then click **Save owner** to get started.")
    st.stop()

owner: Owner = st.session_state.owner
scheduler: Scheduler = st.session_state.scheduler

st.divider()

# ---------------------------------------------------------------------------
# Section 2: Add a pet
# ---------------------------------------------------------------------------
st.subheader("Add a Pet")

with st.form("pet_form"):
    pet_name = st.text_input("Pet name", value="Mochi")
    col1, col2 = st.columns(2)
    with col1:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col2:
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=3)
    pet_notes = st.text_input("Notes (optional)")
    add_pet = st.form_submit_button("Add pet")

if add_pet:
    new_pet = Pet(name=pet_name, species=species, age=int(age), notes=pet_notes)
    if owner.add_pet(new_pet):
        st.success(f"Added pet '{pet_name}'.")
    else:
        st.warning(f"A pet named '{pet_name}' already exists.")

if owner.pets:
    st.markdown("**Pets:**")
    for pet in owner.pets:
        st.text(pet.summary())

st.divider()

# ---------------------------------------------------------------------------
# Section 3: Add a task
# ---------------------------------------------------------------------------
st.subheader("Add a Task")

if not owner.pets:
    st.info("Add a pet first before adding tasks.")
else:
    pet_names = [p.name for p in owner.pets]

    with st.form("task_form"):
        selected_pet_name = st.selectbox("Select pet", pet_names)
        task_name = st.text_input("Task name", value="Morning walk")

        col1, col2, col3 = st.columns(3)
        with col1:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        with col2:
            priority_label = st.selectbox("Priority", ["high", "medium", "low"])
        with col3:
            preferred_time = st.selectbox("Preferred time", ["morning", "afternoon", "evening"])

        category = st.text_input("Category", value="exercise")
        exact_time = st.text_input("Exact start time (HH:MM, optional)", value="")
        recurrence = st.selectbox("Recurrence", ["none", "daily", "weekly"])
        task_notes = st.text_input("Notes (optional)")
        add_task = st.form_submit_button("Add task")

    if add_task:
        priority_map = {"high": 1, "medium": 2, "low": 3}
        recurrence_interval = "" if recurrence == "none" else recurrence

        task = Task(
            name=task_name,
            category=category,
            duration=int(duration),
            priority=priority_map[priority_label],
            preferred_time=preferred_time,
            time=exact_time.strip(),
            recurrence_interval=recurrence_interval,
            notes=task_notes,
        )

        pet = owner.get_pet(selected_pet_name)
        if pet and pet.add_task(task):
            st.success(f"Task '{task_name}' added to {selected_pet_name}.")
        else:
            st.warning("Task could not be added — it may be invalid or already exist.")

    # Show current tasks per pet
    for pet in owner.pets:
        if pet.tasks:
            st.markdown(f"**{pet.name}'s tasks:**")
            rows = []
            for t in pet.tasks:
                rows.append({
                    "Task": t.name,
                    "Category": t.category,
                    "Duration (min)": t.duration,
                    "Priority": {1: "high", 2: "medium", 3: "low"}.get(t.priority),
                    "Preferred Slot": t.preferred_time,
                    "Exact Time": t.time if t.time else "-",
                    "Recurring": t.recurrence_interval if t.recurrence_interval else "no",
                    "Done": "Yes" if t.completed else "No",
                })
            st.table(rows)

st.divider()

# ---------------------------------------------------------------------------
# Section 4: Smart task insights
# ---------------------------------------------------------------------------
st.subheader("Smart Task Insights")

all_tasks = owner.get_all_tasks()

if not all_tasks:
    st.info("Add tasks to see sorting, filtering, and conflict detection.")
else:
    # Conflict warnings
    conflicts = scheduler.detect_conflicts(all_tasks)
    if conflicts:
        st.markdown("**Conflict Warnings:**")
        for warning in conflicts:
            st.warning(warning)
    else:
        st.success("No scheduling conflicts detected.")

    # Filters
    st.markdown("**Filter Tasks**")
    col1, col2, col3 = st.columns(3)

    with col1:
        pet_filter = st.selectbox("Filter by pet", ["All"] + [p.name for p in owner.pets])

    with col2:
        status_filter = st.selectbox("Filter by status", ["All", "Pending", "Completed"])

    with col3:
        categories = sorted({t.category for t in all_tasks})
        category_filter = st.selectbox("Filter by category", ["All"] + categories)

    filtered_tasks = all_tasks

    if pet_filter != "All":
        filtered_tasks = scheduler.filter_tasks_by_pet(filtered_tasks, pet_filter)

    if status_filter == "Pending":
        filtered_tasks = scheduler.filter_tasks_by_status(filtered_tasks, completed=False)
    elif status_filter == "Completed":
        filtered_tasks = scheduler.filter_tasks_by_status(filtered_tasks, completed=True)

    if category_filter != "All":
        filtered_tasks = scheduler.filter_tasks_by_category(filtered_tasks, category_filter)

    # Sorting previews
    st.markdown("**Sorted Task Views**")
    sort_mode = st.radio(
        "Choose sort mode",
        ["Priority + Slot", "Exact Time"],
        horizontal=True,
    )

    if sort_mode == "Priority + Slot":
        display_tasks = scheduler.sort_tasks_by_priority(filtered_tasks)
    else:
        display_tasks = scheduler.sort_by_time(filtered_tasks)

    if display_tasks:
        display_rows = []
        for t in display_tasks:
            display_rows.append({
                "Task": t.name,
                "Category": t.category,
                "Duration": t.duration,
                "Priority": {1: "high", 2: "medium", 3: "low"}.get(t.priority),
                "Preferred Slot": t.preferred_time,
                "Exact Time": t.time if t.time else "-",
                "Recurring": t.recurrence_interval if t.recurrence_interval else "no",
                "Completed": "Yes" if t.completed else "No",
            })
        st.table(display_rows)
    else:
        st.info("No tasks match the selected filters.")

st.divider()

# ---------------------------------------------------------------------------
# Section 5: Generate schedule
# ---------------------------------------------------------------------------
st.subheader("Generate Daily Plan")

if not all_tasks:
    st.info("Add at least one task before generating a plan.")
else:
    if st.button("Generate schedule"):
        st.session_state.plan = scheduler.generate_daily_plan(
            all_tasks,
            owner.available_time_per_day
        )

    if st.session_state.plan is not None:
        plan = st.session_state.plan

        st.markdown(f"**{owner.name}'s plan — {plan.plan_date}**")
        st.caption(
            f"Time available: {plan.total_time_available} min  |  "
            f"Time used: {plan.total_time_used} min  |  "
            f"Free: {plan.total_time_available - plan.total_time_used} min"
        )

        if plan.scheduled_tasks:
            st.markdown("**Scheduled tasks:**")
            scheduled_rows = []
            for t in plan.scheduled_tasks:
                scheduled_rows.append({
                    "Task": t.name,
                    "Duration (min)": t.duration,
                    "Priority": {1: "high", 2: "medium", 3: "low"}.get(t.priority),
                    "Preferred Slot": t.preferred_time,
                    "Exact Time": t.time if t.time else "-",
                    "Recurring": t.recurrence_interval if t.recurrence_interval else "no",
                    "Notes": t.notes,
                })
            st.table(scheduled_rows)
        else:
            st.warning("No tasks could be scheduled.")

        if plan.unscheduled_tasks:
            st.markdown("**Not scheduled:**")
            unscheduled_rows = []
            for task, reason in plan.unscheduled_tasks:
                unscheduled_rows.append({
                    "Task": task.name,
                    "Reason": reason,
                    "Preferred Slot": task.preferred_time,
                    "Exact Time": task.time if task.time else "-",
                })
            st.table(unscheduled_rows)

        with st.expander("Why was each task chosen?"):
            for explanation in plan.explanations:
                st.write(f"- {explanation}")
