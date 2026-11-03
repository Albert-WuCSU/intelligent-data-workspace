"""Explicit LangGraph runtime with no tracing, callbacks, tools or cloud clients."""
from contextlib import contextmanager
from langsmith import tracing_context

@contextmanager
def no_external_tracing():
    # Overrides global/environment tracing enable flags for every graph invocation.
    # Never reads or copies host credentials, and never creates a LangSmith client.
    with tracing_context(enabled=False,client=None,parent=False):yield
