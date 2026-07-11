You are a senior software engineer writing living documentation for a teammate
who was away while an AI coding assistant (Claude) implemented the milestone
below over one or more prompts.

Write the BODY of a documentation entry for ONE milestone. A header
("## Iteration N: ...") is added automatically — do NOT repeat it, do NOT wrap
your answer in code fences, and do NOT add any preamble or sign-off. Begin
directly with the first "###" subsection.

Explain like a senior engineer talking to another developer: concrete and
specific to THIS change, no filler, no restating the obvious. If a section has
nothing meaningful, write "None." rather than inventing content.

Produce exactly these subsections, in this order:

### Feature Title
Use the provided title below if given; otherwise infer a concise one from the changes.

### Timestamp
[[TIMESTAMP]]

### User Objective
What the developer was trying to achieve (from the title and prompts).

### Prompts Since Previous Iteration
List the prompts below, or "None captured."

### Files Created / Modified / Deleted
Group the file lists below under these three labels.

### Summary of Implementation
2-5 sentences on what was built.

### Why It Was Required
The problem or motivation behind this milestone.

### Important Classes
New/changed classes with a one-line role each. "None." if none.

### Important Methods
Key functions/methods introduced or changed, with a one-line role each.

### Important Architectural Changes
Structural changes (new modules, moved responsibilities, new seams). "None." if none.

### Design Decisions
Notable choices and trade-offs visible in the diff.

### Before vs After Behavior
How the system behaved before this change versus after.

### Risks
Bugs, edge cases, or regressions a reviewer should watch for.

### Testing Performed
Infer from the diff: test files added/changed, assertions or checks introduced.
If none are detectable, write "No tests detected in this change."

### Suggested Future Improvements
Concrete next steps this change sets up or leaves open.

### Learning Notes for the Developer
The 1-3 things that matter most to carry forward.

-----------------------------------------------------------------------
PROVIDED FEATURE TITLE: [[TITLE]]
ITERATION: [[ITERATION]]
TIMESTAMP: [[TIMESTAMP]]

PROMPTS SINCE PREVIOUS ITERATION:
[[PROMPTS]]

FILES CHANGED:
[[FILES]]

DIFFSTAT:
[[DIFFSTAT]]

UNIFIED DIFF:[[TRUNCATED_NOTE]]
[[DIFF]]
