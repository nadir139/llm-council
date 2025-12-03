from dotenv import load_dotenv
load_dotenv()  # <-- This loads .env into environment variables

"""Create all database tables in Supabase."""
import asyncio
from database import DatabaseManager

async def create_tables():
    print("🔨 Creating database tables...")

    try:
        # Initialize database
        DatabaseManager.initialize()
        print("✅ Database initialized")

        # Create all tables
        await DatabaseManager.create_tables()
        print("✅ Tables created successfully!")

        # List tables to verify
        session = DatabaseManager.get_session()
        from sqlalchemy import text
        result = await session.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        tables = result.fetchall()

        print("\n📋 Created tables:")
        for table in tables:
            print(f"   - {table[0]}")

        await session.close()
        await DatabaseManager.close()

        print("\n🎉 Database setup complete!")
        print("\nNext steps:")
        print("1. ✅ Database is ready")
        print("2. 🔄 Update main.py to use db_storage")
        print("3. 🧪 Test with backend server")

    except Exception as e:
        print(f"\n❌ Failed to create tables: {e}")
        print("\nMake sure you:")
        print("1. Added DATABASE_URL to .env")
        print("2. Ran test_connection.py successfully first")
        raise

if __name__ == "__main__":
    asyncio.run(create_tables())
