```markdown
----
name: git-operations-version-control
description: Manage source code and collaborate on projects using Git. Perform common version control tasks like committing, branching, merging, rebasing, and resolving conflicts, ensuring history integrity and collaborative efficiency.
License: MIT
----

## Skill Overview

An agent possessing the `git-operations-version-control` skill understands Git's distributed version control system deeply. This includes knowledge of its object model (blobs, trees, commits, tags), the directed acyclic graph (DAG) structure of commits, and the distinction between the working directory, staging area (index), and local repository. The agent can interact with remote repositories, manage branches, handle merge and rebase operations, and resolve conflicts, always prioritizing the integrity and clarity of the project history. A core principle is non-destructive operations on shared history.

## Requirements for Outputs

1.  **Command Execution and Output**:
    *   All Git commands must be executed using a shell or a robust Git library.
    *   Outputs must clearly state the command executed, its standard output (`stdout`), and standard error (`stderr`).
    *   Successful operations should return `0` exit code; failures must return non-zero.
    *   For operations that alter state (e.g., commit, merge, rebase), the resulting commit hash, branch name, or status message must be explicitly reported.
    *   Any warnings or informational messages from Git should be captured and forwarded.

2.  **Error Handling**:
    *   Detect and report Git command failures immediately.
    *   Provide the full `stderr` output from Git when an error occurs.
    *   Suggest common recovery steps for known errors (e.g., "Conflict detected during merge, please resolve and commit," "Failed to push, pull latest changes first").
    *   **Guardrail**: Never attempt to force-push (`git push --force` or `--force-with-lease`) to a shared remote branch unless explicitly instructed with a clear understanding of the risks and prior coordination. Always prioritize safe, non-destructive operations.

3.  **Industry-Standard Conventions**:
    *   **Commit Messages**: Adhere to Conventional Commits specification (e.g., `feat: Add new user authentication`, `fix(auth): Correct password reset flow`, `docs: Update README with installation steps`). Commit messages should be clear, concise, and descriptive.
    *   **Branching Strategies**: While not strictly enforcing one, the agent should be aware of common strategies like GitFlow, GitHub Flow, or GitLab Flow. When creating new branches, use descriptive names (e.g., `feature/user-profile-editing`, `bugfix/login-issue`, `release/v1.2.0`).
    *   **Security**: Never commit sensitive information (passwords, API keys, private certificates) directly into the repository. If such an artifact is detected, immediately flag it and refuse to commit, suggesting `git secret` or environment variables.

## Core Workflows

The agent must be able to perform the following atomic operations:

1.  **Repository Initialization & Cloning**:
    *   **Initialize a new Git repository**:
        ```bash
        git init
        ```
    *   **Clone an existing repository**:
        ```bash
        git clone <repository_url> [destination_path]
        ```

2.  **Making Changes (Working Directory & Staging Area)**:
    *   **Check status**:
        ```bash
        git status
        ```
    *   **Stage changes**:
        ```bash
        git add <file_path> # Stage specific file
        git add .           # Stage all changes in current directory
        ```
    *   **Unstage changes**:
        ```bash
        git reset HEAD <file_path> # Unstage specific file (keep changes in working dir)
        ```
    *   **Discard changes in working directory**:
        ```bash
        git checkout -- <file_path> # Discard changes to a specific file
        git clean -fd               # Remove untracked files and directories (use with caution)
        ```

3.  **Committing Changes**:
    *   **Commit staged changes**:
        ```bash
        git commit -m "type(scope): Subject line" -m "Body paragraph describing changes in detail."
        # Example: git commit -m "feat(auth): Implement user login functionality" -m "Adds endpoint /login and validates user credentials against database."
        ```
    *   **Amend previous commit (use only on unpushed, local commits)**:
        ```bash
        git commit --amend -m "type(scope): Updated subject" # Re-use previous message by omitting -m
        ```

4.  **Branch Management**:
    *   **List branches**:
        ```bash
        git branch -a # List all local and remote branches
        ```
    *   **Create a new branch**:
        ```bash
        git branch <new_branch_name>
        ```
    *   **Switch to a branch**:
        ```bash
        git switch <branch_name> # Recommended for Git 2.23+
        git checkout <branch_name> # Older command
        ```
    *   **Create and switch to a new branch**:
        ```bash
        git switch -c <new_branch_name> # Recommended for Git 2.23+
        git checkout -b <new_branch_name> # Older command
        ```
    *   **Delete a branch (local)**:
        ```bash
        git branch -d <branch_name> # Delete only if merged
        git branch -D <branch_name> # Force delete (use with caution)
        ```

5.  **Remote Operations**:
    *   **List remotes**:
        ```bash
        git remote -v
        ```
    *   **Add a remote**:
        ```bash
        git remote add <name> <url>
        ```
    *   **Fetch changes from a remote**:
        ```bash
        git fetch <remote_name>
        ```
    *   **Pull changes (fetch + merge)**:
        ```bash
        git pull <remote_name> <branch_name>
        ```
    *   **Push changes to a remote**:
        ```bash
        git push <remote_name> <branch_name>
        # To set upstream: git push -u <remote_name> <branch_name>
        ```
    *   **Delete a remote branch**:
        ```bash
        git push <remote_name> --delete <branch_name>
        ```

6.  **Integrating Changes (Merge & Rebase)**:
    *   **Merge a branch**:
        ```bash
        # On target branch (e.g., main)
        git merge <source_branch>
        ```
    *   **Rebase a branch (use only on local, unpushed branches or for cleaning personal history)**:
        ```bash
        # On feature branch
        git rebase <base_branch> # e.g., git rebase main
        # Followed by: git push --force-with-lease <remote> <feature_branch> (if already pushed to origin)
        ```
    *   **Conflict Resolution**:
        *   Identify files with conflicts during merge/rebase (e.g., `git status`).
        *   Manually edit files to resolve conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
        *   Stage resolved files: `git add <conflicted_file>`
        *   Continue merge/rebase: `git merge --continue` or `git rebase --continue`
        *   Abort merge/rebase: `git merge --abort` or `git rebase --abort`

7.  **Inspecting History**:
    *   **View commit log**:
        ```bash
        git log
        git log --oneline --graph --all # Compact, visual log
        ```
    *   **View changes between commits/branches**:
        ```bash
        git diff <commit1> <commit2>
        git diff <branch1> <branch2>
        git diff HEAD~1 HEAD # Changes in last commit
        ```
    *   **View reflog (local history of HEAD movements)**:
        ```bash
        git reflog
        ```
    *   **Blame a file**:
        ```bash
        git blame <file_path>
        ```

8.  **Undoing Changes (Non-Destructive)**:
    *   **Revert a commit (creates a new commit that undoes the changes of a previous commit, preserving history)**:
        ```bash
        git revert <commit_hash>
        ```
    *   **Reset a commit (move HEAD to an earlier commit, preserve or discard changes. Use `--soft` or `--mixed` on pushed commits)**:
        ```bash
        git reset --soft <commit_hash> # Move HEAD, preserve changes staged
        git reset --mixed <commit_hash> # Move HEAD, preserve changes unstaged (default)
        # Never use 'git reset --hard' on shared history.
        ```

## Code Style & Libraries

**Recommended Libraries/Tools**:

*   **Python's `subprocess` module**: For direct execution of Git commands. This provides the most granular control and direct interaction with the Git CLI.
*   **`GitPython` (Optional)**: A Python library that provides object model access to Git repositories. Useful for more complex programmatic interactions, but for basic operations, `subprocess` is often sufficient and more explicit.

**Right vs. Wrong Examples (using `subprocess` in Python)**:

**Right (with error handling and safety)**:

```python
import subprocess
import os

def run_git_command(command_parts, cwd=None, allow_failure=False):
    """Executes a git command and handles its output and errors."""
    full_command = ['git'] + command_parts
    try:
        result = subprocess.run(
            full_command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=not allow_failure, # Raise CalledProcessError if non-zero exit code
            encoding='utf-8',
            errors='replace'
        )
        if not allow_failure and result.returncode != 0:
            print(f"Git command failed: {' '.join(full_command)}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            raise RuntimeError(f"Git command failed with exit code {result.returncode}")
        return result
    except FileNotFoundError:
        print("Error: 'git' command not found. Ensure Git is installed and in PATH.")
        raise
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(full_command)}")
        print(f"STDOUT:\n{e.stdout}")
        print(f"STDERR:\n{e.stderr}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

def add_and_commit(repo_path, files_to_add, commit_message):
    """Stages specified files and creates a new commit."""
    print(f"Adding files: {files_to_add}")
    run_git_command(['add'] + files_to_add, cwd=repo_path)
    print(f"Committing with message: '{commit_message}'")
    run_git_command(['commit', '-m', commit_message], cwd=repo_path)
    print("Commit successful.")

def push_to_remote(repo_path, remote='origin', branch='main', force_push=False):
    """Pushes changes to a remote branch."""
    command = ['push', remote, branch]
    if force_push:
        print("WARNING: Attempting a force push. This can overwrite history!")
        command.append('--force-with-lease') # Safer than --force
    print(f"Pushing to {remote}/{branch}...")
    run_git_command(command, cwd=repo_path)
    print("Push successful.")

# Example Usage:
# repo_dir = "/path/to/my/repo"
# add_and_commit(repo_dir, ['file1.txt', 'src/app.py'], "feat: Add new user profile endpoint")
# push_to_remote(repo_dir, branch='feature/new-feature')

```

**Wrong (lacks error handling, potential for history destruction)**:

```python
import subprocess

# Incomplete error handling, might silently fail or crash
def bad_commit_example(repo_path, message):
    subprocess.run(['git', 'add', '.'], cwd=repo_path)
    subprocess.run(['git', 'commit', '-m', message], cwd=repo_path)

# Direct --force without warning or safety. NEVER do this on shared branches!
def bad_force_push_example(repo_path, remote, branch):
    subprocess.run(['git', 'push', '--force', remote, branch], cwd=repo_path)

# Hard reset on a potentially pushed branch - destroys history
def bad_hard_reset_example(repo_path, num_commits):
    subprocess.run(['git', 'reset', '--hard', f'HEAD~{num_commits}'], cwd=repo_path)
```

## Verification Checklist

Before considering a Git-related task complete, the agent *must* perform the following checks:

1.  **Command Execution Success**: Verify that all Git commands exited with a `0` status code, indicating successful execution.
2.  **Repository State**:
    *   `git status` reports a clean working directory (unless the task explicitly requires an uncommitted state).
    *   The expected branches exist or are deleted as per the task.
    *   The `HEAD` is pointing to the correct branch.
3.  **History Integrity (CRITICAL)**:
    *   **No Unintended History Rewriting**: Confirm that `git push --force` or `git reset --hard` was *not* used on shared branches or commits that have been pushed to a shared remote, unless specifically and explicitly mandated for a very specific, coordinated recovery scenario.
    *   `git log` output shows the intended commit history, no unexpected missing commits or reordering on shared history.
4.  **Remote Synchronization**:
    *   If changes were pushed, verify they appear on the remote repository (e.g., by fetching and checking `git log origin/branch_name`).
    *   If changes were pulled, verify the local branch is up-to-date with the remote.
5.  **Commit Message Quality**: If new commits were created, ensure they adhere to Conventional Commits or any specified project standard and are descriptive.
6.  **Conflict Resolution**: If conflicts occurred, verify they are fully resolved and the resulting code is semantically correct and tested (if testing framework is available).
7.  **Resource Cleanup**: If temporary branches or files were created, ensure they are properly removed unless they are intended to persist.

## Best Practices

1.  **Commit Small, Atomic Changes**: Each commit should represent a single logical change. This makes history easier to understand, revert, and merge.
2.  **Write Clear, Concise, and Conventional Commit Messages**: Follow the Conventional Commits specification. The subject line should be short and informative; the body should explain *why* the change was made, not just *what* was changed.
3.  **Pull/Fetch Frequently**: Always `git pull` or `git fetch` and then merge/rebase from the main development branch before starting new work or pushing changes, to minimize merge conflicts.
4.  **Use Feature Branches**: Perform all new development on separate branches. Never commit directly to `main` (or `master`) or other protected branches.
5.  **Leverage `.gitignore`**: Ensure that temporary files, build artifacts, sensitive configuration files, and `node_modules` (or similar dependency directories) are ignored and never committed.
6.  **Avoid `git push --force` on Shared Branches**: This is the most critical rule for preserving history. Force-pushing rewrites history on the remote and can cause significant problems for collaborators. Use `git push --force-with-lease` if absolutely necessary for a *local* rebase that you know won't clobber others' work, but *never* on shared branches.
7.  **Rebase for Local History Cleanup**: Use `git rebase -i` to squash, reorder, or edit commits on *your local, unpushed branches* before merging or pushing to a shared branch. This creates a clean, linear history.
8.  **Understand `git revert` vs. `git reset`**:
    *   `git revert`: The safe option for undoing changes in a shared history. It creates a new commit that undoes the specified commit(s).
    *   `git reset`: Primarily for local history manipulation. `git reset --soft` or `--mixed` are safer than `--hard` as they preserve working directory changes. Use `--hard` with extreme caution and *only* on local, unpushed changes you are certain you want to discard.
9.  **Utilize `git reflog` for Recovery**: `git reflog` is your "undo" history for `HEAD`. If you accidentally `reset --hard` or lost commits, `reflog` can often help you find and recover them.
10. **Do Not Commit Secrets**: Never commit API keys, passwords, or other sensitive credentials. Use environment variables or dedicated secret management tools. If a secret is accidentally committed, use `git filter-repo` or `BFG Repo-Cleaner` to completely remove it from the repository's history (a complex operation that requires coordination with all collaborators).