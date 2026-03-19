# Status Update CSV Instructions

Use this guide when converting weekly status notes from documents into CSV for Tideline.

## Goal

Produce a UTF-8 CSV that can be imported into one workspace and attached to existing tasks.

Each row should represent one task status update.

## Output Rules

- Return plain CSV only.
- Include exactly these columns, in this order:
  `project_name,task_title,created_at,content,mentions,external_id`
- Always include a header row.
- Use UTF-8 encoding.
- Quote fields when needed under normal CSV rules.
- Do not add markdown, commentary, or extra columns.

## Column Definitions

- `project_name`
  Exact existing project name in Tideline.

- `task_title`
  Exact existing task title in Tideline for that project.

- `created_at`
  ISO-like timestamp for when the weekly update should appear.
  Preferred format: `YYYY-MM-DD HH:MM:SS`
  Example: `2026-03-14 09:00:00`

- `content`
  The full user-facing status update text that should appear on the task.
  Keep it concise but complete.
  Preserve important blockers, decisions, milestone movement, and next steps.

- `mentions`
  Comma-separated person names to associate with the update.
  Use exact person names when known.
  Leave blank if there are no mentions.
  If there is more than one person, keep them in a single CSV field and quote that field.
  Example: `"Jane Smith,Sam Lee"`

- `external_id`
  A stable deduplication key for this specific update row.
  This must stay the same across repeated exports of the same source material.

## Matching Requirements

- `project_name` must match the existing project exactly.
- `task_title` must match the existing task exactly.
- Do not invent new projects or tasks.
- If a source update cannot be mapped confidently to a real task, omit it from the CSV and flag it separately outside the CSV workflow.

## external_id Rules

- Make `external_id` unique per update row.
- Make it deterministic, not random.
- Re-running the parser on the same source should produce the same `external_id`.
- Good pattern:
  `weekly-<date>-<subteam>-<project>-<task>`
- Slugify values:
  lowercase, hyphen-separated, no punctuation beyond hyphens.

Example:

- `weekly-2026-03-14-platform-website-redesign-homepage-qa`

## Content Rules

- Write in direct status-update language.
- Keep tense and formatting consistent across rows.
- Avoid bullet characters inside `content` unless the source truly needs them.
- If a document says a team is blocked, include the blocker explicitly.
- If a document says something is complete, say what completed and what comes next if stated.
- Do not include speculative AI commentary.
- Do not include placeholder text like `TBD`, `unknown`, or `not provided` unless the source literally says that.

## mentions Rules

- Include only people who already exist in the workspace.
- Use exact full names when available.
- Separate multiple names with commas.
- If there are multiple names, quote the whole field so CSV still treats it as one column.
- Correct: `"Jane Smith,Sam Lee"`
- Incorrect: `Jane Smith,Sam Lee` as separate unquoted columns in the row
- Do not include `@` symbols.

## Example

```csv
project_name,task_title,created_at,content,mentions,external_id
Website Redesign,Homepage QA,2026-03-14 09:00:00,"Blocked on final legal copy. QA can resume once the revised language is approved.",Jane Smith,weekly-2026-03-14-web-website-redesign-homepage-qa
Website Redesign,Launch Prep,2026-03-14 09:00:00,"Channel assets are approved and launch checklist review is scheduled for Monday.","Jane Smith,Sam Lee",weekly-2026-03-14-marketing-website-redesign-launch-prep
```

## Final Check Before Returning CSV

- Header row present
- Correct column order
- Exact project names
- Exact task titles
- Stable `external_id` values
- No extra explanation outside the CSV
