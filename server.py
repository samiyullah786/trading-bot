from __future__ import annotations

import argparse
from pathlib import Path

from src.server_core import ServerCore
from src.server_transport import AUREONServer


def main() -> None:
    parser = argparse.ArgumentParser(description="AUREON authoritative server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workspace", type=Path, default=Path("workspace"))
    args = parser.parse_args()

    core = ServerCore(args.workspace)
    server = AUREONServer((args.host, args.port), core.handle)
    print(f"AUREON server listening on {args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
