# import libs.agents.base.exceptions as base_exceptions


class AgentException(Exception):
    """Base class for Agent exceptions."""


class SearchAgentException(AgentException):
    """Base class for SearchAgent exceptions."""
