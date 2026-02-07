"""Sandbox for safe code execution in Saotri Bench."""

from __future__ import annotations

import ast
import multiprocessing
import sys
from typing import Any, Callable


class SandboxError(Exception):
    """Base exception for sandbox errors."""

    pass


class TimeoutError(SandboxError):
    """Raised when code execution times out."""

    pass


class ImportViolationError(SandboxError):
    """Raised when code uses disallowed imports."""

    pass


class ExecutionError(SandboxError):
    """Raised when code fails to execute."""

    pass


def _check_imports(code: str, allowed_imports: list[str]) -> None:
    """Check that code only uses allowed imports.

    Args:
        code: Python source code
        allowed_imports: List of allowed module names

    Raises:
        ImportViolationError: If disallowed imports are found
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ExecutionError(f"Syntax error: {e}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split(".")[0]
                if module_name not in allowed_imports:
                    raise ImportViolationError(
                        f"Import '{module_name}' is not allowed. "
                        f"Allowed imports: {allowed_imports}"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split(".")[0]
                if module_name not in allowed_imports:
                    raise ImportViolationError(
                        f"Import from '{module_name}' is not allowed. "
                        f"Allowed imports: {allowed_imports}"
                    )


def _create_restricted_builtins() -> dict[str, Any]:
    """Create a restricted set of builtins for sandboxed execution."""
    # Safe builtins that don't allow file/network/system access
    safe_builtins = {
        # Types
        "bool": bool,
        "int": int,
        "float": float,
        "str": str,
        "list": list,
        "dict": dict,
        "set": set,
        "frozenset": frozenset,
        "tuple": tuple,
        "bytes": bytes,
        "bytearray": bytearray,
        "complex": complex,
        "type": type,
        "object": object,
        # Functions
        "abs": abs,
        "all": all,
        "any": any,
        "ascii": ascii,
        "bin": bin,
        "callable": callable,
        "chr": chr,
        "divmod": divmod,
        "enumerate": enumerate,
        "filter": filter,
        "format": format,
        "getattr": getattr,
        "hasattr": hasattr,
        "hash": hash,
        "hex": hex,
        "id": id,
        "isinstance": isinstance,
        "issubclass": issubclass,
        "iter": iter,
        "len": len,
        "map": map,
        "max": max,
        "min": min,
        "next": next,
        "oct": oct,
        "ord": ord,
        "pow": pow,
        "print": print,
        "range": range,
        "repr": repr,
        "reversed": reversed,
        "round": round,
        "setattr": setattr,
        "slice": slice,
        "sorted": sorted,
        "sum": sum,
        "zip": zip,
        # Exceptions
        "Exception": Exception,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "AttributeError": AttributeError,
        "RuntimeError": RuntimeError,
        "StopIteration": StopIteration,
        "ZeroDivisionError": ZeroDivisionError,
        "AssertionError": AssertionError,
        "NotImplementedError": NotImplementedError,
        # Constants
        "True": True,
        "False": False,
        "None": None,
        # Allow __import__ for allowed modules (will be filtered by AST check)
        "__import__": __import__,
        "__name__": "__main__",
        "__doc__": None,
    }
    return safe_builtins


def _execute_in_process(
    code: str,
    function_name: str,
    allowed_imports: list[str],
    result_queue: multiprocessing.Queue,
) -> None:
    """Execute code in a separate process and put the function in the queue."""
    try:
        # Create execution namespace with restricted builtins
        namespace: dict[str, Any] = {
            "__builtins__": _create_restricted_builtins(),
        }

        # Pre-import allowed modules
        for module_name in allowed_imports:
            try:
                namespace[module_name] = __import__(module_name)
            except ImportError:
                pass

        # Execute the code
        exec(code, namespace)

        # Get the function
        if function_name not in namespace:
            result_queue.put(
                ("error", f"Function '{function_name}' not found in code")
            )
            return

        func = namespace[function_name]
        if not callable(func):
            result_queue.put(("error", f"'{function_name}' is not callable"))
            return

        # We can't pickle the function, so we'll store the code and namespace info
        result_queue.put(("success", None))

    except Exception as e:
        result_queue.put(("error", f"{type(e).__name__}: {e}"))


def execute_code(
    code: str,
    function_name: str,
    allowed_imports: list[str] | None = None,
    timeout: int = 30,
) -> Callable[..., Any]:
    """Execute code and return the specified function.

    Args:
        code: Python source code containing the function
        function_name: Name of the function to extract
        allowed_imports: List of allowed module names (empty list = no imports allowed)
        timeout: Maximum execution time in seconds

    Returns:
        The extracted function

    Raises:
        TimeoutError: If execution times out
        ImportViolationError: If disallowed imports are used
        ExecutionError: If code fails to execute
    """
    if allowed_imports is None:
        allowed_imports = []

    # Check imports via AST
    _check_imports(code, allowed_imports)

    # Create execution namespace
    namespace: dict[str, Any] = {
        "__builtins__": _create_restricted_builtins(),
    }

    # Pre-import allowed modules
    for module_name in allowed_imports:
        try:
            namespace[module_name] = __import__(module_name)
        except ImportError:
            pass

    # For Windows compatibility, we use a simpler approach:
    # Execute in the current process with a timeout via multiprocessing
    # for the actual function calls (handled by the runner)

    try:
        exec(code, namespace)
    except SyntaxError as e:
        raise ExecutionError(f"Syntax error: {e}")
    except Exception as e:
        raise ExecutionError(f"{type(e).__name__}: {e}")

    # Get the function
    if function_name not in namespace:
        raise ExecutionError(f"Function '{function_name}' not found in code")

    func = namespace[function_name]
    if not callable(func):
        raise ExecutionError(f"'{function_name}' is not callable")

    return func


def execute_with_timeout(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    timeout: int,
) -> Any:
    """Execute a function with a timeout.

    Args:
        func: Function to execute
        args: Arguments to pass to the function
        timeout: Maximum execution time in seconds

    Returns:
        The function result

    Raises:
        TimeoutError: If execution times out
        ExecutionError: If function raises an exception
    """

    def worker(
        func: Callable[..., Any],
        args: tuple[Any, ...],
        result_queue: multiprocessing.Queue,
    ) -> None:
        try:
            result = func(*args)
            result_queue.put(("success", result))
        except Exception as e:
            result_queue.put(("error", f"{type(e).__name__}: {e}"))

    # Use multiprocessing for timeout (works on Windows)
    ctx = multiprocessing.get_context("spawn")
    result_queue: multiprocessing.Queue = ctx.Queue()

    process = ctx.Process(target=worker, args=(func, args, result_queue))
    process.start()
    process.join(timeout=timeout)

    if process.is_alive():
        process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
        raise TimeoutError(f"Execution timed out after {timeout} seconds")

    if result_queue.empty():
        raise ExecutionError("Process ended without returning a result")

    status, result = result_queue.get()
    if status == "error":
        raise ExecutionError(result)

    return result
