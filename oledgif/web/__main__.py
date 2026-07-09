"""Point d'entree : python -m oledgif.web

Demarre le serveur HTTP local (stdlib uniquement) et ouvre le navigateur.
"""

import argparse
import webbrowser
from http.server import ThreadingHTTPServer

from .server import Handler, find_free_port


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m oledgif.web",
        description="Interface web locale pour oledgif (100% local, aucune dependance web).",
    )
    parser.add_argument("--port", type=int, default=None,
                        help="port TCP (defaut: 8100, ou le premier libre a partir de la)")
    parser.add_argument("--no-browser", action="store_true",
                        help="ne pas ouvrir le navigateur automatiquement")
    args = parser.parse_args(argv)

    port = find_free_port(args.port or 8100)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"

    print(f"oledgif web -> {url}")
    print("Ctrl-C pour arreter.")

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("")
        print("arrete.")
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
