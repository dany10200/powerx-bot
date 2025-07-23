from aiohttp import web
import threading

async def handle(request):
    return web.Response(text="Bot is running!")

def run():
    app = web.Application()
    app.router.add_get("/", handle)
    web.run_app(app, host="127.0.0.1", port=8888)

def keep_alive():
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
