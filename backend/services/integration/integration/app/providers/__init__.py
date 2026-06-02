"""Provider adapters — one module per external integration.

Each module exports a class implementing `ProviderAdapter`. The
orchestrator (lands in C4) imports them by name from a small registry.
"""
