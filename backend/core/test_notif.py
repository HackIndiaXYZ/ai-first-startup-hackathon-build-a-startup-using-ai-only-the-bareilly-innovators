import asyncio
from winsdk.windows.ui.notifications.management import UserNotificationListener

async def get_notifs():
    listener = UserNotificationListener.current
    status = await listener.request_access_async()
    
    if status == 1: 
        notifs = await listener.get_notifications_async(1) 
        if notifs:
            print(f"ID: {notifs[0].id}")

if __name__ == "__main__":
    asyncio.run(get_notifs())
