"""Drive the container over a real stdio MCP handshake.

The Glama registry builds this repository's Dockerfile and starts the server
to run its own checks, so the image is verified here rather than assumed to
work. The container runs with --network none: every coefficient is compiled
into the package, so a server that reaches for the network is a bug.

stdin is held open until every reply has been read. Closing it early lets
the server begin shutting down while the last request is still in flight,
which looks exactly like a broken tool call.
"""

from __future__ import annotations

import json
import subprocess
import sys

IMAGE = "thermocouple-its90-mcp:ci"
TIMEOUT_S = 60

failures = 0


def check(name: str, ok: bool, detail: object = None) -> None:
    global failures
    line = ("ok   " if ok else "FAIL ") + name
    if detail is not None:
        line += f"  [{str(detail)[:400]}]"
    print(line, file=sys.stdout if ok else sys.stderr, flush=True)
    if not ok:
        failures += 1


proc = subprocess.Popen(
    ["docker", "run", "--rm", "-i", "--network", "none", IMAGE],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
)


def send(msg: dict) -> None:
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def read_reply(want_id: int) -> dict | None:
    """Read lines until the reply with this id shows up, skipping notifications."""
    while True:
        line = proc.stdout.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict) and msg.get("id") == want_id:
            return msg


try:
    send(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "docker-smoke", "version": "0"},
            },
        }
    )
    init = (read_reply(1) or {}).get("result") or {}
    check("server initializes", bool(init.get("serverInfo")), init.get("serverInfo"))

    send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = ((read_reply(2) or {}).get("result") or {}).get("tools") or []
    names = sorted(t.get("name") for t in tools)
    check(
        "exposes the three tools",
        names
        == [
            "thermocouple_to_emf",
            "thermocouple_to_temperature",
            "thermocouple_types",
        ],
        names,
    )

    for tool in tools:
        ann = tool.get("annotations") or {}
        check(
            f"{tool.get('name')} is annotated read-only",
            ann.get("readOnlyHint") is True and ann.get("destructiveHint") is False,
            ann,
        )

    # Type K at 4.096 mV with the terminals at 25 C is 124.3 C. A naive lookup
    # that ignores the cold junction gives 100.0 C, so this value also proves
    # compensation is actually applied inside the container.
    send(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "thermocouple_to_temperature",
                "arguments": {
                    "type_letter": "K",
                    "emf_mv": 4.096,
                    "reference_c": 25.0,
                },
            },
        }
    )
    res = (read_reply(3) or {}).get("result") or {}
    payload = res.get("structuredContent")
    if payload is None:
        blocks = res.get("content") or []
        if blocks and blocks[0].get("type") == "text":
            try:
                payload = json.loads(blocks[0]["text"])
            except (json.JSONDecodeError, KeyError):
                payload = None
    got = (payload or {}).get("temperature_c")
    check(
        "type K 4.096 mV with 25 C terminals returns 124.3 C",
        got is not None and abs(got - 124.3) < 0.05,
        got if got is not None else res,
    )
finally:
    try:
        proc.stdin.close()
    except OSError:
        pass
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()

if failures:
    print(f"\n{failures} FAILURE(S)", file=sys.stderr)
    print((proc.stderr.read() or "")[-2000:], file=sys.stderr)
    sys.exit(1)
print("\ncontainer works over stdio with the network switched off")
