import asyncio

from models.user import User
import config

user_id = 1

async def main():
    print("User Model")
    user = User()
    print(vars(user))

    print("find by id")
    user = await User().find_by_id(user_id)
    print(user.data(), [user.first_name, user.email])

asyncio.run(main())
