import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to PawPal+, The smart pet care planning assistant.

Use the form below to enter owner and pet information, add care tasks, and generate a daily schedule.
"""
)

# ---------------------------------------------------------------------------
# Session state — application "memory"
# Persists Owner and Scheduler objects across Streamlit reruns.
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
    st.session_state.owner = Owner(
        name=owner_name,
        available_time_per_day=int(available_time),
        preferences={},
    )
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
        st.text(f"  {pet.summary()}")

st.divider()

# ---------------------------------------------------------------------------
# Section 3: Add a task to a pet
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
        recurring = st.checkbox("Recurring daily?")
        task_notes = st.text_input("Notes (optional)")
        add_task = st.form_submit_button("Add task")

    if add_task:
        priority_map = {"high": 1, "medium": 2, "low": 3}
        task = Task(
            name=task_name,
            category=category,
            duration=int(duration),
            priority=priority_map[priority_label],
            preferred_time=preferred_time,
            recurring=recurring,
            notes=task_notes,
        )
        pet = owner.get_pet(selected_pet_name)
        if pet.add_task(task):
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
                    "Time": t.preferred_time,
                    "Done": "Yes" if t.completed else "No",
                })
            st.table(rows)

st.divider()

# ---------------------------------------------------------------------------
# Section 4: Generate schedule
# ---------------------------------------------------------------------------
st.subheader("Generate Daily Plan")

all_tasks = owner.get_all_tasks()

if not all_tasks:
    st.info("Add at least one task before generating a plan.")
else:
    if st.button("Generate schedule"):
        st.session_state.plan = scheduler.generate_daily_plan(all_tasks, owner.available_time_per_day)

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
                    "Time": t.preferred_time,
                    "Notes": t.notes,
                })
            st.table(scheduled_rows)
        else:
            st.warning("No tasks could be scheduled.")

        if plan.unscheduled_tasks:
            st.markdown("**Not scheduled:**")
            for task, reason in plan.unscheduled_tasks:
                st.text(f"  - {task.name}: {reason}")

        with st.expander("Why was each task chosen?"):
            st.text(scheduler.explain_plan(plan))
