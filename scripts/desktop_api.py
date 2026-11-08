"""Desktop-owned API: stdin EOF or 'stop' requests Uvicorn graceful shutdown."""
import sys
import threading
from pathlib import Path


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps/api'))
    import uvicorn
    class DesktopServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets)
            if self.started:
                print('TAKEOFF_DESKTOP_READY', flush=True)

    server = DesktopServer(uvicorn.Config('app.main:app', host='127.0.0.1', port=8000,
                                         log_level='warning', timeout_graceful_shutdown=20))

    def watch_owner():
        sys.stdin.readline()
        server.should_exit = True

    threading.Thread(target=watch_owner, daemon=True).start()
    server.run()


if __name__ == '__main__':
    main()
