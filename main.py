import asyncio
from src.controllers.main_controller import MainController


async def main():
    controller = MainController()
    await controller.run()


if __name__ == "__main__":
    asyncio.run(main())
