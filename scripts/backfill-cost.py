"""Recompute cost_usd for sessions with $0 cost and a known model.

Use after deploying the pricing module to fix legacy rows ingested
before the worker started reconciling cost. Idempotent — re-running is
a no-op for sessions already non-zero.

Usage:
    uv run python scripts/backfill-cost.py [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import text

from viberoi_shared.db import superuser_session
from viberoi_shared.pricing import compute_cost


async def backfill(dry_run: bool) -> None:
    async with superuser_session() as db:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT id, tool_model, tool_pricing_type,
                           tokens_input, tokens_output,
                           tokens_cache_read, tokens_cache_write
                    FROM sessions
                    WHERE total_cost_usd = 0
                    """
                )
            )
        ).all()
        print(f"{len(rows)} sessions with $0 cost")

        updated = 0
        for r in rows:
            sid, model, pricing_type, ti, to, tcr, tcw = r
            cost, est = compute_cost(
                model=model or "",
                input_tokens=ti or 0,
                output_tokens=to or 0,
                cache_read_tokens=tcr or 0,
                cache_write_tokens=tcw or 0,
                pricing_type=pricing_type or "api_key",
            )
            if cost == 0:
                continue
            print(
                f"  {sid}  {model:30s}  ti={ti} to={to}  ->  ${cost:.4f}"
                f"{' (est)' if est else ''}"
            )
            if not dry_run:
                await db.execute(
                    text(
                        "UPDATE sessions SET total_cost_usd = :c, "
                        "is_estimated = :e WHERE id = :id"
                    ),
                    {"c": Decimal(str(cost)), "e": est, "id": sid},
                )
            updated += 1

        print(f"\n{updated} sessions {'would be' if dry_run else 'were'} updated")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(backfill(args.dry_run))


if __name__ == "__main__":
    main()
