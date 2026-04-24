----
name: unix-file-manipulation
description: Skill for interacting with files and directories in a Unix-like environment. Encompasses creation, reading, modification, deletion, permission management, and searching, always prioritizing safety, idempotency, and best practices like temporal file usage. Trigger for any task involving direct manipulation of the filesystem. Do not trigger for database operations or complex application logic outside file I/O. Use its commands and never user the skill name as binary
license: MIT
----

## Requirements for Outputs

1.  **Command Execution Reports**:
    *   For successful commands, output `stdout` and `stderr` (if any) along with the exit code (0 for success).
    *   For failed commands, output `stderr` and the non-zero exit code.
    *   Always report the exact command executed.
    *   Example:
        ```text
        Command: ls -l /nonexistent
        Exit Code: 2
        Stderr: ls: cannot access '/nonexistent': No such file or directory
        ```

2.  **File Content Outputs**:
    *   When asked to read file content, provide the full content, clearly delimited.
    *   For binary files, report "Binary file detected, content not displayed."
    *   When modifying, report the diff (if applicable) or the "before" and "after" state.

3.  **Error Handling**:
    *   **Permissions**: Explicitly check permissions (`test -r`, `test -w`, `test -x`) before attempting operations that might fail due to access rights. Report permission issues clearly.
    *   **File Not Found**: Use `test -f`, `test -d`, `test -e` to verify existence before proceeding. Report "File/Directory not found" if applicable.
    *   **Disk Space**: Though harder to predict, anticipate and report potential `No space left on device` errors if encountered.
    *   **Idempotency**: All operations, especially modifications, must be designed to be idempotent where possible. If an operation is run multiple times, the result should be the same as if it were run once.
    *   **Atomicity**: Critical modifications must be atomic using temporal files and `mv` for final replacement.

4.  **Industry-Standard Conventions**:
    *   **Paths**: Prefer absolute paths (`/path/to/file`) unless explicitly working within a known relative context.
    *   **User Privileges**: Use `sudo` only when absolutely necessary and explicitly requested or clearly implied by the task (e.g., modifying system files). Minimize `sudo` scope.
    *   **Temporary Files**: Always use `mktemp` for creating temporary files and directories. Manage their lifecycle by ensuring deletion upon completion or failure.
    *   **Scripting**: Adhere to POSIX shell scripting best practices (`#!/bin/bash` or `#!/bin/sh`, `set -euo pipefail`).

6. **Identation and file formatting**:
    * For Python files(.py), use:

    ```py
    #To re-indent a block of messy Python code using the AST module, you can use the following pattern:
    import ast
    
    # Messy input with inconsistent indentation
    code = """
    def my_function():
      x = 10
        y = 20
      return x + y
    """
    
    # Parse into an AST
    tree = ast.parse(code)
    
    # Unparse back to clean, indented Python code
    formatted_code = ast.unparse(tree)
    print(formatted_code)

    ``` 
## Core Workflows

Each workflow must prioritize safety, error checking, and idempotency.

### 1. File/Directory Creation

*   **Objective**: Create files or directories with specified content or attributes.
*   **Atomic Steps**:
    1.  **Check Existence**: `test -e "$PATH"`
    2.  **Check Parent Directory Permissions**: `test -w "$(dirname "$PATH")"`
    3.  **Create Directory**: `mkdir -p "$DIRECTORY_PATH"`
    4.  **Create Empty File**: `touch "$FILE_PATH"`
    5.  **Create File with Content**: `echo "$CONTENT" > "$FILE_PATH"` (for simple strings) or use a temporal file (see modification workflow).
    6.  **Set Permissions (Optional)**: `chmod "$PERMS" "$PATH"`
    7.  **Set Ownership (Optional)**: `chown "$USER":"$GROUP" "$PATH"`

### 2. File Reading

*   **Objective**: Retrieve content or metadata of files.
*   **Atomic Stepss**:
    1.  **Check Existence**: `ls -f "$FILE_PATH"`
    2.  **Check Read Permissions**: `ls -r "$FILE_PATH"`
    3.  **Read Content**:
        *   Full file: `cat "$FILE_PATH"`
        *   Head: `head -n "$N" "$FILE_PATH"`
        *   Tail: `tail -n "$N" "$FILE_PATH"`
        <!-- *   Filtered: `grep "$PATTERN" "$FILE_PATH"` -->
    <!-- 4.  **Read Metadata**: `stat "$FILE_PATH"`, `ls -l "$FILE_PATH"` -->

### 3. File Modification (CRITICAL: Use Temporal Files)

*   **Objective**: Safely modify existing files in-place or based on their content.
*   **Atomic Steps**:
    1.  **Check Existence**: `test -f "$FILE_PATH"`
    2.  **Check Read/Write Permissions**: `test -r "$FILE_PATH" && test -w "$FILE_PATH"`
    3.  **Create Temporal File**: `TEMP_FILE=$(mktemp "$FILE_PATH".XXXXXX)`
    4.  **Copy Original Content to Temporal File**: `cp "$FILE_PATH" "$TEMP_FILE"`
    5.  **Perform Modifications on Temporal File**:
        *   Using `sed`: `sed -i.bak "$SED_SCRIPT" "$TEMP_FILE"` (Note: `-i` usually makes backup, but we already have `cp` for robustness, so `sed -f script "$TEMP_FILE" > "$TEMP_FILE.tmp" && mv "$TEMP_FILE.tmp" "$TEMP_FILE"`)
        *   Using `awk`: `awk "$AWK_SCRIPT" "$TEMP_FILE" > "$TEMP_FILE.tmp" && mv "$TEMP_FILE.tmp" "$TEMP_FILE"`
        *   Using `sponge` (from `moreutils`): `cat "$TEMP_FILE" | modify_pipeline | sponge "$TEMP_FILE"`
        *   Using `perl`: `perl -pi -e 's/old/new/g' "$TEMP_FILE"`
        *   For complex logic, iterate lines in shell script, writing to `$TEMP_FILE.tmp` and then `mv`.
    6.  **Verify Temporal File Content (Optional but Recommended)**: Perform checks on `$TEMP_FILE` to ensure modifications are as expected.
    7.  **Atomically Replace Original**: `mv "$TEMP_FILE" "$FILE_PATH"`
    8.  **Clean Up (Crucial)**: Ensure `$TEMP_FILE` (and any other temp files like `*.tmp`) is deleted, possibly with a `trap` statement.
    *   **Guardrail**: NEVER modify a file directly using `>` or `>>` with complex pipelines or `sed -i` without a `cp` pre-backup for critical files. Always use the `mktemp` and `mv` pattern for robust atomic updates.

### 4. File/Directory Deletion

*   **Objective**: Remove files or empty directories.
*   **Atomic Steps**:
    1.  **Check Existence**: `test -e "$PATH"`
    2.  **Check Parent Directory Write Permissions**: `test -w "$(dirname "$PATH")"`
    3.  **Delete File**: `rm "$FILE_PATH"`
    4.  **Delete Empty Directory**: `rmdir "$DIRECTORY_PATH"`
    5.  **Delete Non-Empty Directory (Careful!)**: `rm -r "$DIRECTORY_PATH"` (Requires explicit confirmation or clear intent).
    *   **Guardrail**: Never use `rm -rf /` or similar dangerous commands. Always specify targets explicitly. For recursive deletes, verify the target path rigorously.

### 5. File Copying/Moving

*   **Objective**: Duplicate or relocate files/directories.
*   **Atomic Steps**:
    1.  **Check Source Existence**: `test -e "$SOURCE_PATH"`
    2.  **Check Source Read Permissions**: `test -r "$SOURCE_PATH"`
    3.  **Check Destination Parent Directory Write Permissions**: `test -w "$(dirname "$DEST_PATH")"`
    4.  **Copy File**: `cp "$SOURCE_PATH" "$DEST_PATH"`
        *   Recursive: `cp -r "$SOURCE_PATH" "$DEST_PATH"`
        *   Preserve attributes: `cp -p "$SOURCE_PATH" "$DEST_PATH"`
    5.  **Move File**: `mv "$SOURCE_PATH" "$DEST_PATH"`
        *   **Guardrail**: `mv` is generally atomic within the same filesystem. Cross-filesystem `mv` involves a copy and then delete. Ensure enough space for copy.

### 6. Permissions and Ownership

*   **Objective**: Modify access rights and ownership.
*   **Atomic Steps**:
    1.  **Check Existence**: `test -e "$PATH"`
    2.  **Check Write Permission on File/Directory (for `chmod`)**: `test -w "$PATH"`
    3.  **Check Ownership (for `chown`)**: Requires `sudo` for changing ownership if not owner.
    4.  **Change Permissions**: `chmod "$PERMS" "$PATH"` (e.g., `chmod 644`, `chmod u+x`)
    5.  **Change Ownership**: `chown "$USER":"$GROUP" "$PATH"`

### 7. Archiving and Compression

*   **Objective**: Package files into archives and compress them.
*   **Atomic Steps**:
    1.  **Check Source Existence**: `test -e "$SOURCE_PATH"`
    2.  **Check Destination Parent Directory Write Permissions**: `test -w "$(dirname "$DEST_PATH")"`
    3.  **Create Archive**: `tar -cvf "$ARCHIVE_NAME.tar" "$SOURCE_PATH"`
    4.  **Compress Archive**: `gzip "$ARCHIVE_NAME.tar"` (results in `.tar.gz`) or `tar -czvf "$ARCHIVE_NAME.tar.gz" "$SOURCE_PATH"`
    5.  **Extract Archive**: `tar -xvf "$ARCHIVE_NAME.tar"` or `tar -xzvf "$ARCHIVE_NAME.tar.gz"`
    6.  **Compress/Decompress single file**: `gzip "$FILE"` / `gunzip "$FILE"`

### 8. Searching Files

*   **Objective**: Locate files or directories based on criteria.
*   **Atomic Steps**:
    1.  **Search by Name/Type**: `find "$START_DIR" -name "$PATTERN"` (e.g., `find . -type f -name "*.log"`)
    2.  **Search by Content**: `grep -r "$PATTERN" "$START_DIR"`
    3.  **Search by Size/Time**: `find "$START_DIR" -size +1M -mtime -7`

## Code Style & Libraries

This skill primarily leverages standard POSIX shell utilities.

*   **Shell**: `bash` (preferred for features like arrays, but POSIX `sh` for maximum compatibility).
*   **Core Utilities**: `ls`, `cd`, `pwd`, `mkdir`, `rm`, `rmdir`, `cp`, `mv`, `cat`, `head`, `tail`, `grep`, `sed`, `awk`, `find`, `xargs`, `stat`, `chmod`, `chown`, `tar`, `gzip`, `gunzip`, `mktemp`.
*   **Recommended practices**:
    *   Always use `#!/bin/bash` or `#!/bin/sh` as the shebang.
    *   Start scripts with `set -euo pipefail` for robust error handling.
        *   `set -e`: Exit immediately if a command exits with a non-zero status.
        *   `set -u`: Treat unset variables as an error.
        *   `set -o pipefail`: The return value of a pipeline is the status of the last command to exit with a non-zero status, or zero if all commands exit successfully.
    *   Quote variables to prevent word splitting and globbing issues (e.g., `"$MY_VAR"`).
    *   Use `[[ ... ]]` for conditional expressions in Bash for extended features, or `[ ... ]` for POSIX compatibility.
    *   Implement `trap` for cleanup of temporary files in scripts.

### Right vs. Wrong Code Snippets

**Wrong (Unsafe File Modification):**
```bash
# Don't do this for critical files or complex operations
some_command_output > /etc/my_config.conf
```
*Issue*: If `some_command_output` fails or is interrupted, `/etc/my_config.conf` might be truncated or corrupted.

**Right (Safe & Atomic File Modification):**
```bash
#!/bin/bash
set -euo pipefail

FILE="/etc/my_config.conf"
TEMP_FILE=$(mktemp "$FILE".XXXXXX)

# Ensure temp file is cleaned up on exit (success or failure)
trap 'rm -f "$TEMP_FILE"' EXIT

# Populate the temporal file with the new content
# Example: Append a line
cat "$FILE" > "$TEMP_FILE"
echo "NEW_CONFIG_LINE=value" >> "$TEMP_FILE"

# Or, use a tool like sed to modify in-place on the temp file
# cp "$FILE" "$TEMP_FILE"
# sed -i '/^OLD_LINE=/d' "$TEMP_FILE" # Delete old line
# echo "NEW_LINE=value" >> "$TEMP_FILE" # Add new line

# Validate changes in TEMP_FILE if necessary
# if ! grep "NEW_CONFIG_LINE=value" "$TEMP_FILE"; then
#     echo "Validation failed for $TEMP_FILE" >&2
#     exit 1
# fi

# Atomically replace the original file with the new one
mv "$TEMP_FILE" "$FILE"
echo "Successfully updated $FILE"
```
*Reason*: This ensures the original file is intact until the new, fully written content is ready. `mv` is an atomic operation within the same filesystem.

**Wrong (Hardcoded paths, lack of error checking):**
```bash
rm -rf /tmp/my_app_cache/*
```
*Issue*: If `/tmp/my_app_cache` doesn't exist, this fails silently (or gives an error but proceeds), and `*` might expand to nothing or unintended files.

**Right (Robust deletion):**
```bash
#!/bin/bash
set -euo pipefail

CACHE_DIR="/tmp/my_app_cache"

if [[ -d "$CACHE_DIR" ]]; then
    echo "Clearing cache in $CACHE_DIR..."
    find "$CACHE_DIR" -mindepth 1 -delete # Safer than rm -rf $DIR/*
    echo "Cache cleared."
else
    echo "Cache directory $CACHE_DIR does not exist."
fi
```
*Reason*: Checks for directory existence, uses `find -delete` for safer recursive deletion of contents without removing the directory itself.

## Verification Checklist

Before considering any `unix-file-manipulation` task complete, the agent *must* verify the following:

1.  **Exit Codes**: Was the exit code of the last command `0` (success)? If not, was the non-zero exit code handled and reported?
2.  **File Existence**: Do the expected files/directories exist? (`test -e`, `ls`)
3.  **File Non-Existence**: Are deleted files/directories truly gone? (`test ! -e`)
4.  **Content Verification**: For read/modified files, does the content match the expectation? (`diff`, `grep`, `cat`)
5.  **Permissions/Ownership**: Are permissions (`ls -l`) and ownership (`ls -ld` / `stat`) set correctly?
6.  **Idempotency Check**: If the operation were run again, would it yield the same result without errors or unintended side effects? (e.g., not appending to a file multiple times if it should only appear once).
7.  **Temporary File Cleanup**: Are all temporary files created during the process successfully removed? (Use `ls -a` or `find` in relevant temp directories).
8.  **Output Conformity**: Does the agent's output match the "Requirements for Outputs" section (command reports, content formatting)?
9.  **Guardrail Compliance**: Were any explicit "Do not" rules violated (e.g., hardcoding secrets, unsafe `rm`)?

## Best Practices

*   **`set -euo pipefail`**: Always include this at the top of shell scripts to catch common errors early.
*   **Absolute Paths**: Favor absolute paths (`/var/log/myapp.log`) over relative paths (`./log.log`) to prevent ambiguity, especially in scripts that might be executed from different working directories.
*   **Quote Variables**: Always double-quote variables (`"$VAR"`) to prevent unintended word splitting and glob expansion.
*   **Use `mktemp` for Temporaries**: Never hardcode or guess temporary file names. Always use `mktemp` to generate unique, secure temporary files/directories.
*   **`trap` for Cleanup**: Implement `trap "rm -f '$TEMP_FILE'; exit" INT TERM EXIT` (or similar) to ensure temporary files are cleaned up even if the script is interrupted.
*   **Pre-flight Checks**: Before performing destructive operations (e.g., `rm -r`), check existence, permissions, and possibly even file sizes or modification times to ensure operating on the correct target.
*   **Minimize `sudo`**: If `sudo` is required, use it for the smallest possible scope (e.g., `sudo cp file /dest` instead of `sudo bash -c 'cp file /dest'`).
*   **Disk Space Awareness**: While hard to predict, be mindful of operations that consume significant disk space (e.g., large copies, archive extractions).
*   **Resource Limits**: Be aware of potential resource limits (e.g., `ulimit -n` for open files) for operations involving many files.
*   **Read `man` Pages**: For any utility, refer to its `man` page for the most accurate and comprehensive usage details and options.
*   **Avoid Parsing `ls`**: Do not parse `ls` output in scripts, especially for file names. Use `find -print0 | xargs -0` or shell globs (`*`, `?`) instead.