```markdown
# flawless-hermes-agentic-os Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill covers the core development patterns and conventions found in the `flawless-hermes-agentic-os` Python codebase. It outlines the repository's coding standards, commit practices, and testing strategies, providing clear examples and actionable commands for contributors. While no automated workflows were detected, this guide will help maintain consistency and quality across the project.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - **Example:** `agentManager.py`, `taskHandler.py`

### Import Style
- Use **alias imports** for modules.
  - **Example:**
    ```python
    import numpy as np
    import pandas as pd
    ```

### Export Style
- Use a **mixed export style**; both explicit and implicit exports are present.
  - **Explicit Example:**
    ```python
    __all__ = ['Agent', 'Task']
    ```
  - **Implicit Example:** (no `__all__`, all top-level symbols exported)

### Commit Patterns
- Follow **conventional commit** style.
- Use `feat` as the commit type prefix for new features.
- Commit messages are descriptive, averaging 94 characters.
  - **Example:**  
    ```
    feat: add agent scheduling logic to improve task assignment efficiency
    ```

## Workflows

_No automated workflows were detected in this repository. However, the following manual workflows are recommended:_

### Code Contribution
**Trigger:** When adding or updating features.
**Command:** `/contribute`

1. Create a new branch for your feature or fix.
2. Follow camelCase naming for new files.
3. Use alias imports for any modules.
4. Write or update tests as needed (see Testing Patterns).
5. Commit changes using the conventional commit style (`feat: ...`).
6. Open a pull request for review.

### Testing
**Trigger:** Before merging or deploying changes.
**Command:** `/test`

1. Ensure all `.spec.ts` test files are up to date.
2. Run tests using the `vitest` framework.
   - **Example Command:**  
     ```
     vitest run
     ```
3. Review test results and fix any failures.

## Testing Patterns

- **Framework:** `vitest`
- **Test File Pattern:** `*.spec.ts`
- Tests are written in TypeScript files with `.spec.ts` extension.
- Place test files alongside the modules they test or in a dedicated test directory.
  - **Example:**  
    ```
    agentManager.spec.ts
    ```

## Commands
| Command      | Purpose                                      |
|--------------|----------------------------------------------|
| /contribute  | Start the code contribution workflow         |
| /test        | Run the full test suite with vitest          |
```
