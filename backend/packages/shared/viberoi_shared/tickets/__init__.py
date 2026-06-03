"""CRUD + ORM for tickets and sprints.

Populated by the Integration Service from Jira / Linear / GitHub Issues.
Read by the Worker for attribution and the API for dashboard endpoints.
"""

from viberoi_shared.tickets.models import Sprint, Ticket
from viberoi_shared.tickets.repository import (
    count_tickets_for_sprint,
    find_tickets_by_external_ids,
    get_sprint,
    get_sprint_by_external,
    get_ticket,
    get_ticket_by_external,
    list_active_sprints,
    list_sprints_with_counts,
    list_tickets_for_sprint,
    upsert_sprint,
    upsert_ticket,
)

__all__ = [
    "Sprint",
    "Ticket",
    "count_tickets_for_sprint",
    "find_tickets_by_external_ids",
    "get_sprint",
    "get_sprint_by_external",
    "get_ticket",
    "get_ticket_by_external",
    "list_active_sprints",
    "list_sprints_with_counts",
    "list_tickets_for_sprint",
    "upsert_sprint",
    "upsert_ticket",
]
