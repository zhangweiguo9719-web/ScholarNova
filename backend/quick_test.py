import asyncio
import sys

async def main():
    print("asyncio works")
    print(f"Python {sys.version}")

    # Test SQLAlchemy
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine("sqlite+aiosqlite:///./test_quick.db", connect_args={"check_same_thread": False})
    print("Engine created")

    async with engine.begin() as conn:
        print("Connection OK")
    await engine.dispose()
    print("All tests passed!")

asyncio.run(main())
