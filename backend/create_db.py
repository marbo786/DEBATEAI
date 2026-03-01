import asyncio
import asyncpg
import sys

async def try_create_db():
    passwords = ["marbo786"]
    for pwd in passwords:
        try:
            print(f"Trying password: '{pwd}'...")
            sys.stdout.flush()
            conn = await asyncpg.connect(user="postgres", password=pwd, host="127.0.0.1", database="postgres")
            print(f"Connected successfully with password '{pwd}'")
            try:
                await conn.execute("CREATE DATABASE debateai")
                print("Database 'debateai' created successfully!")
            except asyncpg.exceptions.DuplicateDatabaseError:
                print("Database 'debateai' already exists.")
            await conn.close()
            return
        except asyncpg.exceptions.InvalidPasswordError:
            print("Authentication failed.")
        except Exception as e:
            print(f"Other error: {e}")
    print("Failed to connect with all tried passwords.")

if __name__ == "__main__":
    asyncio.run(try_create_db())
