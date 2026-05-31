# Interview Preparation Guide — Bus Charging Scheduler

This guide tells you exactly what to say in each part of the technical interview.
The words are simple so you can remember and say them easily.
Each section shows which PDF page it comes from.

---

## Before the Interview — Run This First

Open a terminal and run:
```bash
# Show the full scheduling process in the terminal with rich colours
python -m scheduler.engine data/scenarios/scenario_1.json
```

This prints a beautiful coloured output showing exactly how the algorithm works.
**Keep this terminal open during the interview — it is your best demo tool.**

Also open the Streamlit app in a browser:
```bash
streamlit run app.py
```

---

## Part 1 — 30-Second Pitch (say this first)

> "I built a bus charging scheduler in Python and Streamlit.
> Electric buses run from Bengaluru to Kochi — 540 km — and they can only go 240 km
> on one charge, so every bus must stop to charge at least twice.
> My scheduler decides which stations each bus uses and who waits when two buses
> want the same charger at the same time.
> It handles all 5 test scenarios, the UI has 4 tabs, and everything runs in one Python process."

**PDF reference where this is described:**
- Problem statement: PDF page 1, "The problem" section
- 240 km range: PDF page 2, "Physical constants"
- 540 km total route: PDF page 2, "The route" table

---

## Part 2 — Walk Through the Live UI Demo

**Say this while clicking in the browser:**

### Step 1 — Open the app and pick a scenario
> "When you open the app, the first thing you see is the scenario dropdown.
> I have all 5 scenarios pre-loaded. Let me pick Scenario 1 — the baseline case."

*Click the dropdown → select Scenario 1 — Even Spacing*

**PDF reference:** PDF page 9, "A dropdown at the top to pick a scenario"

---

### Step 2 — Show the Input tab
> "The Input tab shows exactly what is being fed into the scheduler.
> You can see all 20 buses — 10 going Bengaluru to Kochi, 10 going the other way.
> Each bus has a departure time, an operator — KPN, Freshbus, or Flixbus —
> and a direction."

*Point to the bus roster table*

> "On the right side, you see the world constants — 60 km/h speed,
> 25-minute charge time, 240 km battery range. And below that, the active weights."

**PDF reference:**
- "A scenario view showing the input (raw data or readable table)": PDF page 9
- 20 buses, 3 operators: PDF page 2, "Buses" section

---

### Step 3 — Show the Per-Bus Timetable
> "The Per-Bus Timetable tab shows what the scheduler decided for each bus.
> Every row is one charging stop. You can see:
> - Which station the bus charged at
> - When it arrived and when it started charging
> - How many minutes it waited in the queue — the yellow cells mean moderate wait,
>   red means long wait
> - The final arrival time at its destination"

*Point to the yellow highlighted cells*

> "Bus-BK-02 waited 10 minutes at station A because bus-BK-01 was still charging.
> This wait contributes to the S1 Individual Wait penalty."

**PDF reference:** PDF page 9, "per-bus timetable — charging stations used, time at each, wait (if any), final arrival"

---

### Step 4 — Show the Per-Station Order
> "The Per-Station Order tab shows, for each charging station,
> the order in which buses charged there.
> Station A served 10 buses in this scenario — all the Bengaluru→Kochi buses
> charge at station A first.
> Bus-BK-01 charged first with no wait. Bus-BK-02 waited 10 minutes.
> Bus-BK-10 waited 90 minutes because it was 10th in line."

*Scroll down to show all 4 station tables*

**PDF reference:** PDF page 9, "per-station view — for each of A, B, C, D, show the order in which buses charged there"

---

### Step 5 — Show the Weight Sliders
> "The three weight sliders control what the scheduler optimises for.
> The PDF says these must be tunable — engineers change them as the system learns
> what matters operationally. They must not be hardcoded."

*Drag the Operator Fairness slider to 2.0*

> "Scenario 4 uses operator weight 2.0 because KPN dominates that scenario.
> Higher operator weight means the scheduler tries harder to equalise wait times
> within each operator's fleet."

**PDF reference:** PDF page 4, "These weights should be tunable — engineers will change them as we learn what matters operationally. Don't hardcode them."

---

### Step 6 — Show the Architecture Tab
> "I added an Architecture tab to make the system design visible.
> It shows the full layer diagram — Presentation, Adapter, Scheduling, Data layers.
> The live rule registry shows all the rules currently registered.
> There is also the anticipated-changes table — every future change this system
> can handle through data alone, with no code changes."

*Click the Architecture tab, open the "Full system diagram" expander*

**PDF reference:** PDF page 11, "ARCHITECTURE.md" deliverable requirements

---

## Part 3 — Explain the Scheduling Algorithm

**Say this when they ask "How does your scheduler work?"**

### Simple explanation (say first):
> "I use a greedy event-driven algorithm.
> Here is what it does step by step:
>
> Step 1: For each charging station, I create a ChargerPool object.
>         The ChargerPool tracks when the charger is free.
>
> Step 2: I sort all 20 buses in order: earliest departure first.
>
> Step 3: For each bus, I try every possible charging plan.
>         A plan is: which stations will this bus charge at?
>         For a Bengaluru-to-Kochi bus, the valid plans are:
>         charge at A and C, or charge at B and C, or charge at B and D.
>
> Step 4: For each plan, I simulate the bus's journey through those stations —
>         I calculate when it arrives, how long it waits, and when it finishes.
>         Then I score the plan using the three soft rules.
>
> Step 5: I commit the cheapest plan and the charger reservations become permanent.
>
> Step 6: After all buses are scheduled, I validate the schedule against
>         all four hard rules."

**Then show the CLI demo:**
> "Let me show you this running in the terminal."

*Run: `python -m scheduler.engine data/scenarios/scenario_1.json`*

*Point to each section of the output:*
> "You can see the scenario panel at the top — this is using the `rich` Python library
> for beautiful terminal output. Then each bus gets committed one by one.
> At the bottom, the station tables show the charge order at each station.
> And the objective score breakdown shows the three penalty values."

**PDF reference:**
- Algorithm requirements: PDF page 4, "Your underlying scheduling framework needs to handle this gracefully"
- "Adding a new rule must not require rewriting the engine": PDF page 4

---

## Part 4 — Explain the Data Structure

**Say this when they ask "Tell me about your data structure design":**

> "The PDF says: 'A scenario IS your data structure.'
> So I designed one Scenario object that holds everything the scheduler needs.
>
> Here is the structure:"

```
Scenario
├── World         → speed=60 km/h, charge_time=25 min, range=240 km
├── Route         → nodes list + segment distances + computed positions dict
├── stations      → {A: 1 charger, B: 1 charger, C: 1 charger, D: 1 charger}
├── Weights       → individual=1.0, operator=1.0, overall=1.0
└── buses         → [Bus(id, operator, origin, destination, departure_min)]
```

> "Everything lives in a JSON file. The engine never reads a file directly —
> it only receives a validated Scenario object from the loader.
> This means I can test the engine without any files at all."

> "All the data classes are immutable — frozen dataclasses.
> Once a Scenario is created, nothing can change it.
> This makes Streamlit caching safe and makes testing easy."

**PDF reference:** PDF page 5, "Designing your data structure (important)" and "A scenario IS your data structure"

---

## Part 5 — Explain the Rule Framework

**Say this when they ask "How would you add a new rule?"**

> "The PDF says: 'Adding a new rule must not require rewriting the engine.'
> I designed a pluggable rule registry to make this possible.
>
> To add a new rule, I create ONE new file in the rules folder.
> No other code changes. Let me show you."

*Open a new file in the terminal or show the example from ARCHITECTURE.md:*

```python
# Create: scheduler/rules/electricity.py

from scheduler.rules.registry import Rule, ScheduleContext, register

@register
class ElectricityCostRule(Rule):
    name = "ElectricityCostRule"
    kind = "soft"
    weight_key = "electricity_cost"

    PEAK_START = 1080   # 18:00 in minutes
    PEAK_END   = 1320   # 22:00 in minutes

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)   # reads from scenario JSON
        penalty = 0.0
        for evt in ctx.charge_events:
            if self.PEAK_START <= evt["start_min"] < self.PEAK_END:
                penalty += ctx.scenario.world.charge_minutes * 2.0
        return weight * penalty
```

> "That is the complete new rule — 15 lines of code.
> The @register decorator adds it to the rule registry.
> The autodiscovery mechanism imports all files in the rules folder automatically.
> The next time the engine runs, it evaluates this rule.
> I add the weight to the scenario JSON and that is it."

**PDF reference:** PDF page 4, "Adding a new rule must not require rewriting the engine — just defining the new rule"

---

## Part 6 — Explain How to Change a Weight

**Say this when they say "Change a weight live":**

> "I open the scenario JSON file — for example, scenario_4.json.
> I find the weights section. I change operator from 1.0 to 3.0.
> That is the entire change. No Python code is touched."

*Open `data/scenarios/scenario_4.json` and show:*
```json
"weights": {
  "individual": 1.0,
  "operator": 3.0,
  "overall": 1.0
}
```

> "Or in the UI, I just drag the Operator Fairness slider.
> The scheduler recalculates immediately with the new weight."

**PDF reference:** PDF page 4, "Changing a weight must be trivial — a value in one obvious place, not scattered across code"

---

## Part 7 — Explain Scalability

**Say this when they ask "How does this scale?"**

> "The PDF says: 'Your scheduler must be built to scale.'
> My design handles three types of scaling:
>
> 1. More buses — just add them to the JSON. The engine is O(buses × plans × stations).
>    For 100 buses it is still fast — milliseconds.
>
> 2. More stations — add a node to route.nodes, a segment to route.segments,
>    and an entry in stations. No code changes.
>
> 3. New rules — add one file with @register. No engine changes.
>
> If the scale ever grows to thousands of buses, I can replace the greedy algorithm
> with a CP-SAT solver behind the same Strategy interface. The rules, data model,
> and UI are unchanged."

**PDF reference:** PDF page 4, "The one thing we really care about: Your scheduler must be built to scale"

---

## Part 8 — Answer the Hard Questions

### "Why did you choose greedy instead of an optimisation solver?"

> "There are three reasons:
>
> First, the scale is small — 20 buses, 4 stations, 3 candidate plans per bus.
> A greedy algorithm runs in milliseconds. I do not need a heavy solver.
>
> Second, the assignment specifically grades extensibility —
> 'adding a new rule must not require rewriting the engine.'
> With a solver like CP-SAT, adding a new constraint means remodelling the whole problem.
> With my pluggable registry, I add one file.
>
> Third, the greedy approach is fully explainable.
> I can trace every decision: 'bus-BK-02 chose plan A to C because its cost was 735,
> lower than plan B to C which cost 875.'
> A solver gives you an optimal answer but you cannot easily explain why."

**PDF reference:** PDF page 12, "Approach: Did you pick a scheduling approach that's the right fit? Can you defend why?"

---

### "The weights don't seem to change the schedule — is that a bug?"

> "No, it is expected behaviour. Here is why:
>
> In Scenario 1, all Bengaluru-to-Kochi buses must charge at station A first —
> it is the only station within 240 km of Bengaluru.
> So the queue order at station A is always determined by arrival order.
>
> The weight slider changes the total objective score — you can see this number
> change in the Objective Breakdown expander. But it does not always change
> the physical station assignment because the range constraints force only
> one valid first station.
>
> This is documented in ARCHITECTURE.md, Section 1.
> Scenario 4 shows weight sensitivity better — it has more operator diversity."

---

### "How would you handle driver shift constraints?"

> "I would add one hard rule: DriverShiftRule.
> I would add a shift_end_min field to the Bus data class in the JSON.
> Then one new rule file checks: if the bus arrives after the driver's shift ends,
> return math.inf — that plan is rejected.
> Zero engine code changes."

---

### "What was the hardest part?"

> "The hardest part was the ChargerPool rollback mechanism.
> During plan evaluation, I tentatively reserve charger slots.
> But I need to test multiple plans, so I must undo each tentative reservation
> before testing the next plan.
>
> I solved this with snapshot and restore methods on ChargerPool.
> Before testing a plan: snapshot() saves the pool state.
> After scoring: restore() undoes the reservation.
> Only the winning plan is re-simulated permanently.
>
> You can see this pattern clearly in scheduler/engine.py in the greedy loop."

---

## Part 9 — Run a New Scenario Live

**If they hand you a new schedule to encode (PDF page 13):**

Steps:
1. Copy `data/scenarios/scenario_1.json` → `data/scenarios/scenario_6.json`
2. Change the `name` field
3. Replace the `buses` array with the new buses
4. Each bus needs: id, operator, origin, destination, departure_min
5. Save — the app discovers it automatically on next load

**Quick time-to-minutes converter:**
```
19:00 = 1140    19:08 = 1148    19:15 = 1155    19:30 = 1170
19:45 = 1185    20:00 = 1200    20:15 = 1215    20:30 = 1230
20:45 = 1245    21:00 = 1260    21:15 = 1275    21:30 = 1290
```

Formula: `hours × 60 + minutes = departure_min`
Example: 20:25 → `20 × 60 + 25 = 1225`

---

## Summary Diagram — What to Point to During the Demo

```
Terminal output                    Browser UI
(python -m scheduler.engine)       (streamlit run app.py)
─────────────────────────────     ──────────────────────────────────
                                   ┌── Sidebar ──────────────────┐
╭─── Scenario ────────────╮        │ Scenario: [dropdown]        │
│ Scenario 1              │        │ Weights: [sliders]          │
│ buses=20  stations=4    │        │ Reset weights [button]      │
╰─────────────────────────╯        └─────────────────────────────┘

✓ bus-BK-01  KPN   A→C  wait=0    ┌── Input Tab ────────────────┐
✓ bus-BK-02  FBU   A→C  wait=10   │ Bus roster table            │
✓ bus-BK-03  FLX   A→C  wait=20   │ World constants             │
...                                │ Route info + raw JSON       │
                                   └─────────────────────────────┘
┌── Station A ─────────────────┐
│ # │ Bus ID   │ Wait │ Start  │  ┌── Per-Bus Timetable Tab ────┐
│ 1 │ bus-BK-01│   0  │ 20:40  │  │ Yellow = moderate wait      │
│ 2 │ bus-BK-02│  10  │ 21:05  │  │ Red = long wait (>30 min)   │
└──────────────────────────────┘  └─────────────────────────────┘

┌── Objective Score ─────────────┐ ┌── Per-Station Order Tab ───┐
│ IndividualWaitRule │  900.0    │ │ 4 expandable station tables│
│ OperatorRule       │ 2864.3    │ └─────────────────────────────┘
│ OverallRule        │  815.0    │
│ TOTAL              │ 4579.3    │ ┌── Architecture Tab ─────────┐
└───────────────────────────────┘ │ Full system diagram         │
                                  │ Live rule registry          │
                                  │ Anticipated changes table   │
                                  └─────────────────────────────┘
```

---

## PDF Page Reference Index

| PDF Page | Topic | Where in code |
|----------|-------|---------------|
| Page 1 | Problem: route Bengaluru→A→B→C→D→Kochi | `scheduler/model.py` Route class |
| Page 2 | Physical constants: 240km, 25min, same speed | `scheduler/model.py` World class |
| Page 2 | Route table: 100+120+100+120+100=540 km | `data/scenarios/scenario_1.json` route.segments |
| Page 2 | 20 buses, 3 operators | `data/scenarios/scenario_1.json` buses array |
| Page 3 | Hard rule H1: range constraint | `scheduler/rules/hard_rules.py` RangeRule |
| Page 3 | Hard rule H2: route order | `scheduler/rules/hard_rules.py` RouteOrderRule |
| Page 3 | Hard rule H3: one bus per charger | `scheduler/resources.py` ChargerPool |
| Page 3 | Hard rule H4: charge = exactly 25 min | `scheduler/rules/hard_rules.py` ChargeDurationRule |
| Page 4 | Soft rule S1: individual wait | `scheduler/rules/soft_rules.py` IndividualWaitRule |
| Page 4 | Soft rule S2: operator fairness | `scheduler/rules/soft_rules.py` OperatorRule |
| Page 4 | Soft rule S3: overall makespan | `scheduler/rules/soft_rules.py` OverallRule |
| Page 4 | "Don't hardcode weights" | `scheduler/model.py` Weights.get() |
| Page 4 | "Adding a new rule must not rewrite engine" | `scheduler/rules/_discover.py` autodiscovery |
| Page 5 | "A scenario IS your data structure" | `scheduler/model.py` Scenario class |
| Page 9 | UI: dropdown, per-bus tab, per-station tab | `frontend/tabs.py` |
| Page 10 | Deliverables: ARCHITECTURE.md | `ARCHITECTURE.md` |
| Page 12 | How we evaluate: approach, scalability | `ARCHITECTURE.md` sections 1-3 |

---

## What to Say When Nervous

If you cannot remember something, say one of these:

> "Let me show you the code — the comments explain exactly what is happening."

> "I documented this decision in ARCHITECTURE.md — let me open that."

> "The PDF requirement for this is on page [number] — I referenced it in the code comments."

These are honest, professional answers. The code is well-documented so you can always point to it.
