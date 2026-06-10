"""Backfill C-numbers for existing contracts that were created before the contract_number generation was added."""
import asyncio
from sqlalchemy import text
from app.kernel.database.session import TenantAwareSessionFactory
from app.config import settings


async def backfill():
    factory = TenantAwareSessionFactory(settings.database_url)
    session = await factory.create_session(
        "00000000-0000-4000-8000-000000000001", "system", "admin"
    )

    sql1 = text(
        """UPDATE contract_reviews
           SET metadata = metadata || '{"contract_number": "C06202604"}'::jsonb
           WHERE review_id = '3477e08b-ea8b-43bc-a45a-ab0c3c593074'
             AND tenant_id = '00000000-0000-4000-8000-000000000001'"""
    )
    sql2 = text(
        """UPDATE contract_reviews
           SET metadata = metadata || '{"contract_number": "C06202605"}'::jsonb
           WHERE review_id = 'f1ac973a-8775-4175-bc9b-ac2cf4582b07'
             AND tenant_id = '00000000-0000-4000-8000-000000000001'"""
    )

    await session.execute(sql1)
    await session.execute(sql2)
    await session.commit()
    print("Backfill complete")
    await session.close()


asyncio.run(backfill())
