"""Quick test to verify database connectivity."""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

async def test_connection():
    print(f"Testing connection to: {DATABASE_URL[:50]}...")
    
    try:
        # Test 1: Basic connection
        print("\n1️⃣ Testing basic asyncpg connection...")
        conn = await asyncio.wait_for(
            asyncpg.connect(DATABASE_URL, ssl=False),
            timeout=10.0
        )
        print("✅ Connection successful!")
        
        # Test 2: Simple query
        print("\n2️⃣ Running test query...")
        result = await conn.fetchval("SELECT NOW();")
        print(f"✅ Query successful! Server time: {result}")
        
        await conn.close()
        print("\n✅ ALL TESTS PASSED")
        
    except asyncio.TimeoutError:
        print("❌ Connection timed out - network issue suspected")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
