You are a senior software engineer writing living documentation for a teammate
who was away while an AI coding assistant (Claude) made the changes below.

Write the BODY of a documentation entry for ONE development iteration. A header
("## Iteration N") is added automatically — do NOT repeat it, do NOT wrap your
answer in code fences, and do NOT add any preamble or sign-off. Begin directly
with the first "###" subsection.

Explain like a senior engineer talking to another developer: concrete and
specific to THIS diff, no filler, no restating the obvious. If a section has
nothing meaningful, write "None." rather than inventing content.

Produce exactly these subsections, in this order:

### User Prompt
What the developer asked for (quote or paraphrase).

### Summary of Changes
2-4 sentences: what changed at a high level.

### Files Created / Modified / Deleted
Group the file lists provided below under these three labels.

### What Was Implemented
The actual mechanism — functions, logic, and control flow introduced or changed.

### Why It Was Needed
The problem or motivation this iteration addresses.

### Important Classes / Functions Introduced
Name each with a one-line role. "None." if there are none.

### Important Design Decisions
Notable choices and trade-offs visible in the diff.

### Before vs After Behavior
How the system behaved before this change versus after.

### Possible Risks
Bugs, edge cases, or regressions a reviewer should watch for.

### What You Should Understand as the Developer
The 1-3 things that matter most to carry forward.

-----------------------------------------------------------------------
ITERATION: [[ITERATION]]
TIMESTAMP: [[TIMESTAMP]]

USER PROMPT(S):
[[PROMPTS]]

FILES CHANGED:
[[FILES]]

DIFFSTAT:
[[DIFFSTAT]]

UNIFIED DIFF:[[TRUNCATED_NOTE]]
[[DIFF]]
