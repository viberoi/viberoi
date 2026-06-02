"""Pydantic request/response models for the Ingest service.

Validation happens at the HTTP boundary; nothing past `app/` should ever
see a raw dict. Shared domain types come from `viberoi_shared.types`.
"""
