Commit all changes and push to current branch.

Follow these steps:

1. Run `git status` and `git diff` (both staged and unstaged) to understand all changes
2. Run `git log -1 --format='%s'` to see the last commit message style
3. Analyze the changes and generate a concise, descriptive commit message that:
   - Summarizes the nature of changes (feature, fix, refactor, docs, etc.)
   - Focuses on the "what" and "why" rather than implementation details
   - Uses imperative mood (e.g., "Add feature" not "Added feature")
   - Keeps the first line under 72 characters
   - Follows the repository's commit message style
4. Stage all changes with `git add .`
5. Create the commit with the generated message, including the Claude Code attribution:
   ```
   git commit -m "$(cat <<'EOF'
   [Your generated commit message here]

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   ```
6. Push to the current branch with `git push`
7. Display the commit SHA and summary of what was pushed

IMPORTANT:
- Do NOT commit if there are no changes (check git status first)
- Do NOT push if the repository is not connected to a remote
- If pre-commit hooks modify files, check if amend is safe before using --amend
- Never use --force or --force-with-lease
- If push fails, display the error and ask user how to proceed
