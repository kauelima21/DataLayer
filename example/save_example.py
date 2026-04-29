import asyncio

from models.user import User
import config

async def main():
    create = False
    if create:
        print("create example")

        user = User()
        user.first_name = "John"
        user.last_name = "Doe"
        user.email = "john.doe@mail.com"
        user.role = "admin"

        await user.save()

        print("user saved")

    update = True
    if update:
        print("update example")

        user = await User().find_by_id(1)
        user.first_name = "Joanne"
        user.email = "joanne.doe@mail.com"
        user.role = "common"

        await user.save()

        print("user saved")


asyncio.run(main())