def green(s: str):
    return f"\033[0;32m{s}\033[0m"


SUCCESS = green("[SUCCESS]")
WAITING = "\033[1;33m[WAITING]\033[0m"
FAILURE = "\033[0;31m[FAILURE]\033[0m"
