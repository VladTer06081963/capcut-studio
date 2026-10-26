---
name: worktree-review
description: Review repository state and changes without staging, cleaning, or publishing them.
---

# Worktree review

1. Begin with `git status --short`; inspect only the files relevant to the
   user's request.
2. Distinguish tracked edits, untracked source, local configuration, symlinks,
   generated output, and media. Do not assume untracked means disposable.
3. Read the complete relevant files and diffs before recommending or editing.
4. Never run `git add .`, reset, checkout, clean, or broad delete commands.
   Never stage, commit, push, or open a PR unless the user explicitly requests
   that exact action.
5. For documentation-only changes, validate internal links/path names and run
   `git diff --check`. For code, choose and run the narrowest relevant test.
6. Report facts separately from assumptions; mention pre-existing unrelated
   worktree state without attributing it to the current task.

Do not read secrets, `.env`, user auth/config directories, or external library
contents as part of a routine review.
