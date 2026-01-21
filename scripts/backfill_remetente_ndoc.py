"""Backfill script: copy shipments.rem_nDoc into shipment_invoices.remetente_ndoc in batches.

Usage:
    poetry run python scripts/backfill_remetente_ndoc.py

This script runs in small batches and reports progress; it's safe to run multiple times (idempotent).
"""
import asyncio
from sqlalchemy import select, update
from app.db import AsyncSessionLocal, engine, ensure_db_initialized
from app.models.shipment import ShipmentInvoice, Shipment
from loguru import logger

BATCH_SIZE = 1000

async def run_backfill():
    await ensure_db_initialized()
    async with AsyncSessionLocal() as session:
        while True:
            # Find a batch of invoice ids that are missing remetente_ndoc but have shipments.rem_nDoc
            q = (select(ShipmentInvoice.id, Shipment.rem_nDoc)
                 .join(Shipment, Shipment.id == ShipmentInvoice.shipment_id)
                 .where((ShipmentInvoice.remetente_ndoc == None) | (ShipmentInvoice.remetente_ndoc == ''))
                 .where(Shipment.rem_nDoc != None)
                 .limit(BATCH_SIZE))
            res = await session.execute(q)
            rows = res.all()
            if not rows:
                logger.info("No more rows to backfill. Exiting.")
                break

            ids = [r[0] for r in rows]
            # Build update
            stmt = (
                update(ShipmentInvoice)
                .where(ShipmentInvoice.id.in_(ids))
                .values(remetente_ndoc=Shipment.rem_nDoc)
            )
            # Use correlation via join in raw SQL because SQLAlchemy update with correlated subquery is complex
            # Fall back to per-row update as simpler and safe approach
            for invoice_id, rem_nDoc in rows:
                await session.execute(
                    update(ShipmentInvoice).where(ShipmentInvoice.id == invoice_id).values(remetente_ndoc=rem_nDoc)
                )
            await session.commit()
            logger.info("Backfilled %d invoices", len(ids))


if __name__ == '__main__':
    asyncio.run(run_backfill())
