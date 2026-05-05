```markdown
----
name: python-simplifier
description: This skill enables an AI agent to refactor complex, verbose, or unclear Python code into simpler, more readable, and maintainable forms. It focuses on improving code clarity, adhering to PEP 8, adding comprehensive line-by-line comments, and structuring code for future extension using abstract base classes where appropriate.
license: MIT
----

## Skill Overview

The `python-simplifier` skill is designed for agents to transform intricate, hard-to-read, or overly verbose Python code into a streamlined, highly maintainable, and easily understandable format. The primary goal is to enhance code clarity, promote adherence to Pythonic principles (e.g., PEP 8), and explicitly document every functional aspect of the code through detailed comments. A crucial aspect is enabling future extensibility and robust design patterns by leveraging Abstract Base Classes (`abc.ABC`) when defining interfaces for components. This skill ensures that the output code is not only functionally equivalent but also a paradigm of clarity and best practices.

## Requirements for Outputs

To ensure the highest quality and consistency, all outputs generated using the `python-simplifier` skill must adhere to the following stringent requirements:

### Formatting Standards
1.  **PEP 8 Compliance**: All generated code must strictly adhere to PEP 8 style guide. This includes, but is not limited to, 4-space indentation, line length limits (79 characters for code, 72 for docstrings/comments), consistent spacing, and naming conventions (`snake_case` for functions/variables, `PascalCase` for classes).
2.  **Readability**: Code structure must prioritize human readability. This means appropriate use of whitespace, logical grouping of statements, and avoiding overly dense or "clever" one-liners that compromise clarity.
3.  **Logical Flow**: The control flow within functions and methods should be straightforward and easy to follow, avoiding excessive nesting where simpler alternatives exist.

### Error-Handling Rules
1.  **Specific Exceptions**: All `try...except` blocks must catch specific exception types (e.g., `FileNotFoundError`, `ValueError`, `TypeError`). Catching broad `Exception` is strictly forbidden unless immediately re-raised after logging, or if it's a top-level catch-all in an application entry point with graceful shutdown.
2.  **Informative Messages**: Error messages should be clear, concise, and provide sufficient context for debugging. They must indicate what went wrong, where, and potentially why.
3.  **Graceful Degradation**: Where applicable, code should handle anticipated errors gracefully, preventing crashes and allowing the program to continue in a degraded but stable state.

### Industry-Standard Conventions
1.  **Pythonic Idioms**: Utilize Python's built-in features and standard library effectively (e.g., list comprehensions, `enumerate`, `zip`, `context managers`). Avoid C-style loops where Pythonic alternatives offer clearer or more concise solutions.
2.  **Modularity**: Promote single responsibility principle. Functions and classes should have a clear, focused purpose.
3.  **No Global State Abuse**: Minimize reliance on mutable global variables.
4.  **Abstract Base Classes (ABC) for Interfaces**: When designing classes that serve as interfaces or contracts for future implementations, they *must* inherit from `abc.ABC` (from the `abc` module). Abstract methods that must be implemented by concrete subclasses *must* be decorated with `@abc.abstractmethod`. This ensures clear contracts and type checking.

### Commenting Standards (CRITICAL)
1.  **Docstrings**:
    *   **Module-level**: Every Python file (module) must start with a docstring explaining its overall purpose and contents.
    *   **Class-level**: Every class must have a docstring explaining its role, key attributes, and how it's intended to be used. If it's an `abc.ABC`, the docstring must clearly state its role as an interface or abstract base for specific functionality.
    *   **Function/Method-level**: Every function and method must have a docstring detailing its purpose, arguments (type hints where appropriate), return values, and any exceptions it might raise. Use a consistent format (e.g., Google Style or reStructuredText).
2.  **Inline Comments (Line-by-Line/Block-by-Block)**:
    *   **Every line or logical block of code *must* have an inline comment.** This comment should clearly describe **what the line/block does** and **what its specific purpose is within the larger function/method context**.
    *   Comments should explain *why* a particular decision was made if it's not immediately obvious.
    *   Avoid redundant comments that simply re-state the obvious (e.g., `# Increment counter` for `count += 1` is usually unnecessary unless the intent is complex). Focus on intent and high-level purpose for obvious lines, and detailed mechanics for complex ones.

## Core Workflows

The `python-simplifier` agent follows a methodical, multi-stage workflow to refactor and simplify Python code.

### Workflow 1: Initial Code Analysis and Problem Identification

1.  **Parse and Represent (Internal AST)**:
    *   Internally parse the provided Python code into an Abstract Syntax Tree (AST) for structural analysis. This allows for programmatic inspection without execution.
    *   *Comment*: This step converts the raw code into a structured tree, making it easier to analyze its components and relationships without running it.

2.  **Complexity Metrics Calculation**:
    *   Calculate cyclomatic complexity for functions and methods. High complexity (e.g., > 10-15) indicates potential areas for simplification.
    *   Identify nested depth of conditional statements and loops. Deep nesting (e.g., > 3 levels) is a strong indicator of simplification opportunity.
    *   Measure function/method length (lines of code). Overly long functions are candidates for extraction.
    *   *Comment*: These metrics quantify how intricate the code is, guiding the focus towards the most complex parts first.

3.  **Pattern Recognition for Simplification**:
    *   **Redundancy**: Detect repeated code blocks (DRY violation) that can be extracted into functions or methods.
    *   **Unclear Logic**: Identify overly complex boolean expressions, ambiguous variable names, or non-idiomatic constructs.
    *   **Inefficient Data Structures/Algorithms**: Note if sub-optimal data structures (e.g., list for frequent lookups instead of dictionary/set) or algorithms are used. (Prioritize clarity first, then efficiency if obvious).
    *   **Poor Error Handling**: Flag broad `except` clauses, missing `finally`, or unhandled edge cases.
    *   **Lack of Modularity**: Identify large functions/classes attempting to do too many things.
    *   *Comment*: This step scans the code for common issues that make it hard to understand and maintain, pinpointing specific areas for improvement.

### Workflow 2: Refactoring and Simplification Execution

1.  **Standardize Formatting (PEP 8)**:
    *   Apply standard PEP 8 formatting rules: correct indentation, spacing, line length, and consistent naming conventions.
    *   *Comment*: Ensures the code adheres to Python's community style guide, improving baseline readability.

2.  **Improve Naming Conventions**:
    *   Rename ambiguous or non-descriptive variables, functions, and class names to be clear, concise, and reflect their purpose.
    *   *Comment*: Using meaningful names makes the code's intent self-evident, reducing the need for excessive explanation.

3.  **Extract Functions/Methods**:
    *   Break down large, complex functions or methods into smaller, single-purpose helper functions/methods.
    *   Pass necessary data as arguments and return results.
    *   *Comment*: Decomposes complex logic into manageable, reusable units, improving modularity and testability.

4.  **Simplify Conditional Logic and Loops**:
    *   Refactor nested `if/else` statements into flatter structures using early returns, guard clauses, or dictionary lookups where appropriate.
    *   Replace explicit `for` loops with list comprehensions, set comprehensions, or generator expressions when they improve readability and conciseness.
    *   Utilize `any()`, `all()`, `filter()`, `map()` for common collection operations.
    *   *Comment*: Reduces cognitive load by making decision points and iterations simpler and more direct.

5.  **Refactor Error Handling**:
    *   Replace generic `except Exception:` with specific exception types.
    *   Add `try...except...else...finally` blocks where appropriate for robust resource management and error recovery.
    *   Ensure custom exceptions are raised for specific application-level errors.
    *   *Comment*: Improves the reliability of the code by precisely handling expected issues and providing clear diagnostics for unexpected ones.

6.  **Apply Abstract Base Classes (ABC) for Interfaces**:
    *   If the input code defines a class that acts as a blueprint or contract for other classes (e.g., a "strategy" interface, a common base for different data sources), convert it to inherit from `abc.ABC`.
    *   Mark methods that *must* be implemented by concrete subclasses with `@abc.abstractmethod`.
    *   *Comment*: Establishes clear contractual obligations for subclasses, enforcing a consistent interface and enabling better design patterns.

### Workflow 3: Documentation and Verification

1.  **Generate/Improve Docstrings**:
    *   Add or refine module, class, and function/method docstrings. Ensure they accurately describe the entity's purpose, parameters, return values, and exceptions.
    *   For ABCs, explicitly state their role as an interface or abstract base.
    *   *Comment*: Provides high-level documentation, explaining what each major component does.

2.  **Add Line-by-Line/Block-by-Block Inline Comments (CRITICAL)**:
    *   Iterate through the *entire* refactored codebase.
    *   For every line or logical block of code, add an inline comment explaining **what it does** and **what its specific purpose or intent is**.
    *   If a line's purpose is immediately obvious (e.g., `x = 1`), focus on its contribution to the larger logic. If complex, detail its mechanics.
    *   *Comment*: This is the most granular documentation layer, ensuring that *every single step* of the code's execution path is transparent and understandable.

3.  **Functional Equivalence Testing (Conceptual)**:
    *   Conceptually, verify that the simplified code produces identical outputs and side effects as the original code for a given set of inputs. This often requires running existing tests or comparing behavior.
    *   *Comment*: Confirms that simplification did not alter the intended behavior of the program.

## Code Style & Libraries

### Recommended Libraries
*   **`abc`**: (Built-in) Essential for defining Abstract Base Classes, ensuring interfaces are correctly implemented.
*   **`typing`**: (Built-in) For adding type hints to improve code clarity and enable static analysis.
*   **`ast`**: (Built-in) Useful for internal static analysis and transformation if complex code manipulation is required.
*   **`flake8` / `black` / `isort`**: (Conceptual) While not used directly to write code, the agent's output should be compliant with the standards enforced by these tools.

### "Right vs. Wrong" Code Snippets

**1. Generic vs. Specific Exception Handling**

**Wrong:**
```python
def process_data_wrong(file_path: str): # Defines a function to process data from a file path
    try: # Starts a block of code to monitor for exceptions
        with open(file_path, 'r') as f: # Attempts to open the file in read mode
            data = f.read() # Reads all content from the file into the 'data' variable
        result = int(data) / 0 # Attempts to convert data to integer and then divide by zero (intentional error)
        return result # Returns the calculated result
    except Exception as e: # Catches any type of exception that occurs
        print(f"An error occurred: {e}") # Prints a generic error message
        return None # Returns None to indicate failure
```

**Right:**
```python
import abc # Imports the Abstract Base Classes module for defining interfaces

def process_data_right(file_path: str) -> int | None:
    """
    Processes data from a specified file path, attempting to convert its content to an integer.
    
    This function reads content from a file, attempts to convert it to an integer,
    and then performs a division (demonstrating specific error handling for division by zero).
    
    Args:
        file_path (str): The path to the file to be processed.
    
    Returns:
        int | None: The result of the division if successful, otherwise None if an error occurs.
    
    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file content cannot be converted to an integer.
        ZeroDivisionError: If the integer conversion results in a division by zero scenario.
    """
    try: # Initiates a block of code that is monitored for potential exceptions during execution.
        # Open the file specified by file_path in read mode.
        # The 'with' statement ensures the file is properly closed after its block, even if errors occur.
        with open(file_path, 'r') as f: 
            # Read all the content from the opened file and store it in the 'file_content' variable.
            file_content = f.read() 
        
        # Attempt to convert the string content from the file into an integer.
        numeric_value = int(file_content) 
        
        # Perform an arithmetic operation: divide the numeric_value by 10 (as a demonstration).
        # This line is primarily to create a scenario where a ZeroDivisionError could occur for demonstration,
        # if numeric_value were 0 and the divisor was also 0, or if numeric_value itself was 0.
        # For simplicity, we assume a non-zero divisor here for normal operation.
        result = numeric_value // 10 
        
        # Return the computed result after successful processing.
        return result 
    
    except FileNotFoundError: # Catches the specific exception raised when the file_path does not point to an existing file.
        # Print an informative error message indicating the file was not found.
        print(f"Error: File not found at '{file_path}'") 
        # Return None to signal that the operation failed due to a missing file.
        return None 
    
    except ValueError: # Catches the specific exception raised when int() receives a non-numeric string.
        # Print an informative error message, specifying that the file content couldn't be converted to an integer.
        print(f"Error: File content '{file_content}' is not a valid integer.") 
        # Return None to signal that the operation failed due to invalid file content.
        return None 
    
    except ZeroDivisionError: # Catches the specific exception raised if a division by zero occurs (e.g., if result becomes infinite).
        # Print an informative error message about the division by zero.
        print("Error: Division by zero occurred during calculation.") 
        # Return None to signal that the operation failed due to an arithmetic error.
        return None 
    
    except Exception as e: # As a final fallback, catch any other unforeseen exceptions.
        # This catch-all should be used sparingly and only if no more specific handler is possible,
        # or for top-level application error reporting.
        print(f"An unexpected error occurred: {e}") 
        # Return None to indicate a general, unhandled failure.
        return None
```

**2. Class without ABC vs. Class with ABC (for interfaces)**

**Wrong:**
```python
class DataProcessor: # Defines a class named DataProcessor
    def process(self, data): # Defines a method named process that takes 'self' and 'data'
        raise NotImplementedError # Raises an error indicating this method needs to be implemented
    
    def transform(self, data): # Defines another method named transform
        raise NotImplementedError # Raises an error indicating this method also needs to be implemented

class CsvProcessor(DataProcessor): # Defines CsvProcessor which inherits from DataProcessor
    def process(self, data): # Implements the process method for CSV data
        # Logic for processing CSV
        print(f"Processing CSV data: {data}") # Prints a message
        return [row.split(',') for row in data.splitlines()] # Splits data into rows and then by comma
    
    # Missing transform implementation, but the base class doesn't enforce it.
```

**Right:**
```python
import abc # Imports the Abstract Base Classes module, necessary for defining abstract classes.
from typing import Any, List # Imports type hints for better code readability and static analysis.

class AbstractDataProcessor(abc.ABC): # Declares an abstract base class named AbstractDataProcessor, inheriting from abc.ABC.
    """
    Abstract base class defining the interface for data processing components.
    
    This class acts as a contract, ensuring that any concrete implementation
    of a data processor provides specific methods for data processing and transformation.
    """
    @abc.abstractmethod # Decorator indicating that this method must be implemented by concrete subclasses.
    def process(self, data: Any) -> Any: # Defines an abstract method 'process' that takes any type of data and returns any type.
        """
        Processes raw input data according to the specific implementation.
        
        Args:
            data (Any): The raw data to be processed.
        
        Returns:
            Any: The processed data.
        """
        # This method is abstract and provides no implementation in the base class.
        pass # The 'pass' statement serves as a placeholder for the abstract method.

    @abc.abstractmethod # Decorator indicating that this method must also be implemented by concrete subclasses.
    def transform(self, processed_data: Any) -> Any: # Defines an abstract method 'transform' for further data manipulation.
        """
        Transforms the already processed data into a desired output format.
        
        Args:
            processed_data (Any): The data that has already been processed.
        
        Returns:
            Any: The transformed data.
        """
        # This method is also abstract and provides no implementation in the base class.
        pass # The 'pass' statement serves as a placeholder for the abstract method.

class CsvProcessor(AbstractDataProcessor): # Defines CsvProcessor, which explicitly inherits from AbstractDataProcessor.
    """
    Concrete implementation of an AbstractDataProcessor for handling CSV formatted data.
    
    This class specifically processes and transforms string data that is expected to be in CSV format.
    """
    def process(self, data: str) -> List[List[str]]: # Implements the 'process' method as required by the abstract base class.
        """
        Processes raw CSV string data into a list of lists (rows and columns).
        
        Args:
            data (str): A string containing CSV formatted data.
        
        Returns:
            List[List[str]]: A list where each inner list represents a row of CSV values.
        """
        # Print a message indicating the type of data being processed for debugging/logging.
        print(f"Processing CSV data: {data[:50]}...") # Shows the beginning of the data.
        # Split the input string data by newline characters to get individual rows.
        # Then, for each row, split it by commas to get individual cell values.
        # This creates a list of lists, where each inner list is a row of string columns.
        rows = [row.split(',') for row in data.splitlines() if row.strip()] 
        # Return the processed data structure.
        return rows 

    def transform(self, processed_data: List[List[str]]) -> str: # Implements the 'transform' method, also required by the abstract base class.
        """
        Transforms processed CSV data (list of lists) back into a single CSV string.
        
        Args:
            processed_data (List[List[str]]): The data already processed into a list of lists.
        
        Returns:
            str: A single string representing the data in CSV format.
        """
        # Print a message indicating the transformation is taking place.
        print("Transforming CSV data back to string.") 
        # For each row in the processed data, join the elements with commas to form a CSV line.
        # Then, join all these lines with newline characters to create the final CSV string.
        csv_string = '\n'.join([','.join(row) for row in processed_data]) 
        # Return the transformed CSV string.
        return csv_string 

# Example of how an attempt to instantiate CsvProcessor without implementing a required abstract method
# would raise a TypeError at runtime, enforcing the contract.
# Example: class IncompleteProcessor(AbstractDataProcessor): pass
# This would raise: TypeError: Can't instantiate abstract class IncompleteProcessor with abstract method process, transform
```

**3. Poorly Commented & Complex vs. Well-Commented & Simplified**

**Wrong:**
```python
def calc(items, tax_rate, disc): # Calculates something.
    tot = 0 # Initialize total.
    for i in items: # Loop through items.
        if i > 100: # Check condition.
            tot += i * (1 - disc) # Apply discount.
        else: # Else branch.
            tot += i # Add item without discount.
    final = tot * (1 + tax_rate) # Apply tax.
    return final # Return result.
```

**Right:**
```python
from typing import List # Imports List for type hinting to specify expected data types.

def calculate_final_price(items: List[float], tax_rate: float, discount_percentage: float) -> float:
    """
    Calculates the final total price of a list of items after applying conditional discounts and a sales tax.
    
    Items above a certain threshold (100.0) receive a specified discount.
    A sales tax is applied to the entire subtotal after discounts.
    
    Args:
        items (List[float]): A list of individual item prices.
        tax_rate (float): The sales tax rate to be applied (e.g., 0.05 for 5%).
        discount_percentage (float): The discount rate for high-value items (e.g., 0.10 for 10%).
    
    Returns:
        float: The final calculated total price, including discounts and tax.
    """
    # Initialize the subtotal before any taxes are applied.
    subtotal_before_tax = 0.0 

    # Iterate through each item price in the provided list of items.
    for item_price in items: 
        # Check if the current item's price exceeds the discount threshold of 100.0.
        if item_price > 100.0: 
            # If the item price is high, apply the discount to this specific item.
            # The formula `item_price * (1 - discount_percentage)` calculates the price after discount.
            discounted_price = item_price * (1.0 - discount_percentage) 
            # Add the discounted item price to the running subtotal.
            subtotal_before_tax += discounted_price 
        else: 
            # If the item price is not high enough for a discount, add it to the subtotal as is.
            subtotal_before_tax += item_price 
    
    # After calculating the subtotal from all items and their respective discounts,
    # apply the overall sales tax rate to this subtotal.
    # The formula `subtotal_before_tax * (1.0 + tax_rate)` computes the final price including tax.
    final_price_after_tax = subtotal_before_tax * (1.0 + tax_rate) 
    
    # Return the final calculated price to the caller.
    return final_price_after_tax 
```

## Verification Checklist

Before considering any task complete, the `python-simplifier` agent *must* perform the following mandatory checks:

*   [ ] **Functional Equivalence**: Does the simplified code produce exactly the same outputs and exhibit the same side effects as the original code for all valid inputs? (Requires conceptual "testing" against original behavior).
*   [ ] **PEP 8 Compliance**: Is the entire codebase compliant with PEP 8? (e.g., passing a `flake8` or `pylint` check without errors or warnings related to style).
*   [ ] **Comprehensive Docstrings**: Does every module, class, function, and method have a clear, accurate, and properly formatted docstring?
*   [ ] **Line-by-Line Commenting**: Has every line or logical block of code been accompanied by an inline comment explaining **what it does** and **what its specific purpose/intent is**?
*   [ ] **Descriptive Naming**: Are all variable, function, method, and class names descriptive, unambiguous, and consistent with their roles?
*   [ ] **Abstract Base Class Usage**: Are `abc.ABC` and `@abc.abstractmethod` correctly used for classes that define an interface or contract for future extensions?
*   [ ] **Specific Error Handling**: Are `try...except` blocks catching specific exceptions, and are error messages informative? Is generic `except Exception:` avoided unless explicitly justified and re-raising/logging?
*   [ ] **Reduced Complexity**: Has cyclomatic complexity been reduced in identified complex functions/methods? (e.g., reduced nesting, extracted functions).
*   [ ] **No Redundancy**: Has repeated code been refactored into reusable functions, methods, or classes?
*   [ ] **Code Clarity**: Is the overall control flow clear, logical, and easy to follow without excessive cognitive load?

## Best Practices

### Performance Tips
*   **Prioritize Clarity First**: Never sacrifice clarity for micro-optimizations unless a specific performance bottleneck has been identified through profiling. A simpler, readable solution is often easier to optimize later.
*   **Leverage Built-ins and C-Extensions**: Prefer Python's built-in functions, types (e.g., `list`, `dict`, `set`), and standard library modules over custom implementations when they offer equivalent or better performance. Many are implemented in C.
*   **List Comprehensions/Generators**: Use list comprehensions, set comprehensions, or generator expressions for creating collections or iterating where they provide a more concise and often faster alternative to explicit `for` loops.
*   **Avoid Repeated Computations**: Cache results of expensive computations if they are used multiple times with the same inputs.
*   **Choose Right Data Structures**: Select appropriate data structures for the task (e.g., `set` for fast membership testing, `dict` for key-value lookups, `collections.deque` for efficient appends/pops from both ends).

### Common Pitfalls
*   **Premature Optimization**: Trying to make code faster before knowing where the actual bottlenecks are. This often leads to complex, hard-to-read code that isn't significantly faster.
*   **Altering Behavior**: Introducing new bugs or changing the original functional behavior during simplification. **The simplified code MUST be functionally identical.**
*   **Over-Abstraction**: Creating too many layers of abstraction or too many small classes/functions when simple inline code or a single function would suffice. Abstraction should solve a problem, not create complexity.
*   **Ignoring Context**: Simplifying code without understanding its broader context or performance requirements. Some complexity might be necessary due to external integrations, domain constraints, or strict performance needs. Aim for *clear* complexity, not hidden complexity.
*   **Removing Necessary Comments**: Deleting comments that explain complex logic, trade-offs, or non-obvious design decisions. While self-documenting code is ideal, non-obvious parts still require explicit explanation.
*   **Hardcoding Values**: Do not hardcode configurations, API keys, file paths, or other sensitive/environment-specific data. Utilize environment variables, configuration files (e.g., `.ini`, YAML, JSON), or command-line arguments.
*   **Using `eval()` or `exec()` Unnecessarily**: Avoid these functions unless absolutely necessary for a specific meta-programming task, as they pose significant security risks and make code harder to analyze.