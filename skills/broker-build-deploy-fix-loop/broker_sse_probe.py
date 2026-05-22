"""End-to-end SSE probe for the Lumina broker dev deployment.

Mints the same x5c+JWT credentials as probe_broker_auth.py, then sends a
brokered request with Accept: text/event-stream to a live SSE upstream.

Default upstream:
  https://stream.wikimedia.org/v2/stream/recentchange

Environment overrides:
  BROKER_HOST                 Target broker host.
  SSE_TARGET_URI              SSE upstream URL.
  SSE_USER_AGENT              User-Agent sent to the upstream through broker.
  SSE_MAX_FIRST_LINE_SECONDS  Max allowed time to first non-empty SSE line.
  SSE_READ_WINDOW_SECONDS     Max time spent reading SSE lines.
  SSE_MIN_NONEMPTY_LINES      Minimum non-empty SSE lines required.
"""
import ssl
import sys
import time
import urllib.error
import urllib.request
import os

import probe_broker_auth as probe

SSE_TARGET_URI = os.environ.get(
    "SSE_TARGET_URI",
    "https://stream.wikimedia.org/v2/stream/recentchange",
)
SSE_USER_AGENT = os.environ.get(
    "SSE_USER_AGENT",
    "LuminaSandboxBroker-SSE-Probe/1.0 (lixiangliu@microsoft.com)",
)
MAX_FIRST_LINE_SECONDS = float(os.environ.get("SSE_MAX_FIRST_LINE_SECONDS", "30"))
READ_WINDOW_SECONDS = float(os.environ.get("SSE_READ_WINDOW_SECONDS", "60"))
MIN_NONEMPTY_LINES = int(os.environ.get("SSE_MIN_NONEMPTY_LINES", "8"))


def main() -> int:
    pfx = probe.download_pfx()
    key, _chain, thumbprint, x5c = probe.load_chain(pfx)
    token = probe.mint_token(key, thumbprint, exp_offset=600)

    req = urllib.request.Request(probe.PROXY_ROOT_URL, method="GET")
    req.add_header(probe.TARGET_URI_HEADER, SSE_TARGET_URI)
    req.add_header(probe.TOKEN_HEADER, token)
    req.add_header(probe.X5C_HEADER, x5c)
    req.add_header("Accept", "text/event-stream")
    req.add_header("Cache-Control", "no-cache")
    req.add_header("User-Agent", SSE_USER_AGENT)

    print(f"[info] broker={probe.PROXY_ROOT_URL}")
    print(f"[info] target={SSE_TARGET_URI}")
    print(f"[info] user-agent={SSE_USER_AGENT}")

    start = time.time()
    try:
        response = urllib.request.urlopen(
            req,
            context=ssl.create_default_context(),
            timeout=max(READ_WINDOW_SECONDS + 30, 90),
        )
    except urllib.error.HTTPError as error:
        body = error.read()[:1000].decode(errors="replace")
        print(f"[FAIL] HTTP {error.code} opening SSE stream")
        if body:
            print(body)
        return 1

    with response:
        content_type = response.headers.get("content-type", "")
        print(f"[info] status={response.status}")
        print(f"[info] content-type={content_type}")

        if response.status != 200:
            print(f"[FAIL] Expected HTTP 200, got {response.status}")
            return 1

        if not content_type.lower().startswith("text/event-stream"):
            print("[FAIL] Expected content-type to start with text/event-stream")
            return 1

        first_line_at = None
        event_lines = []
        deadline = time.time() + READ_WINDOW_SECONDS
        while time.time() < deadline and len(event_lines) < MIN_NONEMPTY_LINES:
            line = response.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            if not text:
                continue
            if first_line_at is None:
                first_line_at = time.time() - start
            event_lines.append(text[:180])

    if first_line_at is None:
        print("[FAIL] No non-empty SSE lines received")
        return 1

    print(f"[info] time_to_first_nonempty_line={first_line_at:.3f}s")
    print(f"[info] nonempty_lines_read={len(event_lines)}")
    for index, line in enumerate(event_lines, 1):
        print(f"[info] line[{index}]={line}")

    if first_line_at > MAX_FIRST_LINE_SECONDS:
        print(
            "[FAIL] First SSE line was too slow; this can indicate buffering "
            f"or upstream delay. max={MAX_FIRST_LINE_SECONDS}s"
        )
        return 1

    if len(event_lines) < MIN_NONEMPTY_LINES:
        print(
            f"[FAIL] Expected at least {MIN_NONEMPTY_LINES} non-empty SSE lines, "
            f"got {len(event_lines)}"
        )
        return 1

    print("SSE probe passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
