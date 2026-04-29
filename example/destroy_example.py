import asyncio

from models.user import User
import config

user_id = 1

async def main():
    user = await User().find_by_id(user_id)
    await user.destroy()
    print("user destroyed")

asyncio.run(main())
