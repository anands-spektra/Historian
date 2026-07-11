You are a principal engineer writing PROJECT_ARCHITECTURE.md for a codebase you
are documenting for the whole team. Base everything ONLY on the context below
(the iteration log, file tree, and source excerpts). Do not invent components
that are not present.

Output a complete, well-structured Markdown document. Start with a top-level
"# Project Architecture" title. Use Mermaid diagrams (```mermaid blocks) where
they genuinely aid understanding, and make sure the Mermaid syntax is valid.

Cover, using only what the context supports (write "Not applicable" for any that
genuinely do not apply):

- Overall architecture (the big picture, in prose + a Mermaid component diagram)
- Folder structure and what each part holds
- Major modules and their responsibilities
- Request flow / control flow (Mermaid sequence diagram if useful)
- Data flow (Mermaid diagram if useful)
- Dependency graph (how modules depend on each other)
- Important design patterns actually used
- Key classes and functions
- Key interfaces / extension seams
- Configuration and environment variables
- External services and APIs
- Anything a new engineer must know to navigate the code

Be concrete and specific to THIS project. No filler.

=======================================================================
CONTEXT
=======================================================================
[[CONTEXT]]
