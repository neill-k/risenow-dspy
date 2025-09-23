"""Async utilities for parallel DSPy agent execution."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Callable
import dspy
from dspy import Prediction
import time

logger = logging.getLogger(__name__)


async def run_agent_async(
    agent_func: Callable,
    *args,
    **kwargs
) -> Any:
    """
    Run a DSPy agent function asynchronously.

    Uses asyncio.to_thread to run the agent in a thread pool,
    avoiding blocking the event loop while maintaining thread safety.
    """
    try:
        # Run the agent function in a thread pool
        result = await asyncio.to_thread(agent_func, *args, **kwargs)
        return result
    except Exception as e:
        logger.error(f"Error running agent async: {e}")
        raise


async def run_agents_parallel(
    tasks: List[Tuple[Callable, tuple, dict]],
    max_concurrent: int = 3,
    timeout: Optional[float] = 300.0,
) -> List[Any]:
    """
    Run multiple agent functions in parallel using asyncio.

    Parameters
    ----------
    tasks : List[Tuple[Callable, tuple, dict]]
        List of (function, args, kwargs) tuples to execute
    max_concurrent : int
        Maximum number of concurrent tasks
    timeout : float
        Timeout in seconds for each task

    Returns
    -------
    List[Any]
        Results from each task (None for failed tasks)
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_with_semaphore(func, args, kwargs, index):
        async with semaphore:
            try:
                logger.info(f"Starting task {index}: {func.__name__}")
                start_time = time.time()

                if timeout:
                    result = await asyncio.wait_for(
                        run_agent_async(func, *args, **kwargs),
                        timeout=timeout
                    )
                else:
                    result = await run_agent_async(func, *args, **kwargs)

                elapsed = time.time() - start_time
                logger.info(f"Completed task {index} in {elapsed:.2f}s")
                return result

            except asyncio.TimeoutError:
                logger.error(f"Task {index} timed out after {timeout}s")
                return None
            except Exception as e:
                logger.error(f"Task {index} failed: {e}")
                return None

    # Create tasks with semaphore
    async_tasks = [
        run_with_semaphore(func, args, kwargs, i)
        for i, (func, args, kwargs) in enumerate(tasks)
    ]

    # Run all tasks
    results = await asyncio.gather(*async_tasks, return_exceptions=False)
    return results


async def run_parallel_analysis(
    vendor_func: Optional[Callable] = None,
    vendor_args: tuple = (),
    vendor_kwargs: dict = None,
    pestle_func: Optional[Callable] = None,
    pestle_args: tuple = (),
    pestle_kwargs: dict = None,
    porters_func: Optional[Callable] = None,
    porters_args: tuple = (),
    porters_kwargs: dict = None,
    timeout: float = 300.0,
) -> Dict[str, Any]:
    """
    Run vendor, PESTLE, and Porter's analyses in parallel.

    Returns
    -------
    Dict[str, Any]
        Dictionary with keys 'vendor', 'pestle', 'porters' containing results
    """
    tasks = []
    task_names = []

    if vendor_func:
        tasks.append(run_agent_async(
            vendor_func,
            *vendor_args,
            **(vendor_kwargs or {})
        ))
        task_names.append('vendor')

    if pestle_func:
        tasks.append(run_agent_async(
            pestle_func,
            *pestle_args,
            **(pestle_kwargs or {})
        ))
        task_names.append('pestle')

    if porters_func:
        tasks.append(run_agent_async(
            porters_func,
            *porters_args,
            **(porters_kwargs or {})
        ))
        task_names.append('porters')

    # Run with timeout
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"Parallel analysis timed out after {timeout}s")
        results = [None] * len(tasks)

    # Map results to names
    result_dict = {}
    for name, result in zip(task_names, results):
        if isinstance(result, Exception):
            logger.error(f"{name} analysis failed: {result}")
            result_dict[name] = None
        else:
            result_dict[name] = result

    return result_dict


def run_async(async_func, *args, **kwargs):
    """
    Convenience wrapper to run an async function from sync code.

    Creates a new event loop if needed (useful for Jupyter/scripts).
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we're here, we're already in an async context
        raise RuntimeError("Cannot use run_async from within an async context")
    except RuntimeError:
        # No event loop running, create one
        return asyncio.run(async_func(*args, **kwargs))


class AsyncDSPyBatch:
    """
    Wrapper for batch processing DSPy modules with async support.
    """

    def __init__(self, module: dspy.Module):
        """Initialize with a DSPy module."""
        self.module = module

    async def process_batch_async(
        self,
        examples: List[dspy.Example],
        max_concurrent: int = 5,
        timeout: float = 30.0
    ) -> List[Any]:
        """
        Process a batch of examples asynchronously.

        Parameters
        ----------
        examples : List[dspy.Example]
            List of examples to process
        max_concurrent : int
            Maximum concurrent processing
        timeout : float
            Timeout per example

        Returns
        -------
        List[Any]
            Results for each example
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_one(example, index):
            async with semaphore:
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(self.module.forward, **example.inputs()),
                        timeout=timeout
                    )
                    return result
                except asyncio.TimeoutError:
                    logger.error(f"Example {index} timed out")
                    return None
                except Exception as e:
                    logger.error(f"Example {index} failed: {e}")
                    return None

        tasks = [process_one(ex, i) for i, ex in enumerate(examples)]
        return await asyncio.gather(*tasks)

    def process_batch(
        self,
        examples: List[dspy.Example],
        max_concurrent: int = 5,
        timeout: float = 30.0
    ) -> List[Any]:
        """Sync wrapper for process_batch_async."""
        return run_async(
            self.process_batch_async,
            examples,
            max_concurrent,
            timeout
        )


async def batch_with_progress(
    module: dspy.Module,
    examples: List[dspy.Example],
    progress_callback: Optional[Callable[[int, int], None]] = None,
    max_concurrent: int = 5,
) -> List[Any]:
    """
    Process batch with progress callbacks.

    Parameters
    ----------
    module : dspy.Module
        DSPy module to use
    examples : List[dspy.Example]
        Examples to process
    progress_callback : Callable
        Function called with (completed, total)
    max_concurrent : int
        Maximum concurrent tasks
    """
    completed = 0
    total = len(examples)
    results = [None] * total

    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_callback(example, index):
        nonlocal completed
        async with semaphore:
            try:
                result = await asyncio.to_thread(
                    module.forward,
                    **example.inputs()
                )
                results[index] = result
            except Exception as e:
                logger.error(f"Failed processing example {index}: {e}")
                results[index] = None
            finally:
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)

    tasks = [process_with_callback(ex, i) for i, ex in enumerate(examples)]
    await asyncio.gather(*tasks)

    return results