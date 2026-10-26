import asyncio
from mangum import Mangum
from .app import app

adapter = Mangum(app, lifespan="off")


def handler(event, context):
    # Python 3.14 no longer creates a default loop for synchronous callers.
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop is None or loop.is_closed():
        asyncio.set_event_loop(asyncio.new_event_loop())
    return adapter(event, context)
