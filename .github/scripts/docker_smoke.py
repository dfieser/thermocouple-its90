"""Drive the container over a real stdio MCP handshake.

The Glama registry builds this repository's Dockerfile and starts the server
to run its own checks, so the image is verified here rather than assumed to
work. The container runs with --network none: every coefficient is compiled
into the package, so a server that reaches for the network is a bug.
"""

from __future__ import annotations

import json
import subprocess
import sys

IMAGE = "thermocouple-its90-mcp:ci"

REQUESTS = [
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "docker-smoke", "version": "0"},
        },
    },
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "thermocouple_to_temperature",
            "arguments": {"type_letter": "K", "emf_mv": 4.096, "reference_c": 25.0},
        },
    },
]

failures = 0


def check(name: str, ok: bool, detail: object = None) -> None:
    global failures
    line = ("ok   " if ok else "FAIL ") + name
    if detail is not None:
        line += f"  [{str(detail)[:300]}]"
    print(line, file=sys.stdout if ok else sys.stderr)
    if not ok:
        failures += 1


stdin = "".join(json.dumps(r) + "\n" for r in REQUESTS)
proc = subprocess.run(
    ["docker", "run", "--rm", "-i", "--network", "none", IMAGE],
    input=stdin,
    capture_output=True,
    text=True,
    timeout=180,
)

responses = {}
for line in proc.stdout.splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue
    if isinstance(msg, dict) and msg.get("id") is not None:
        responses[msg["id"]] = msg

if not responses:
    print("no JSON-RPC responses; container stderr follows:", file=sys.stderr)
    print(proc.stderr[-3000:], file=sys.stderr)
    sys.exit(1)

init = responses.get(1, {}).get("result", {})
check("server initializes", bool(init.get("serverInfo")), init.get("serverInfo"))

tools = responses.get(2, {}).get("result", {}).get("tools", [])
names = sorted(t.get("name") for t in tools)
check(
    "exposes the three tools",
    names
    == ["thermocouple_to_emf", "thermocouple_to_temperature", "thermocouple_types"],
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
call = responses.get(3, {}).get("result", {})
payload = None
for block in call.get("content", []):
    if block.get("type") == "text":
        try:
            payload = json.loads(block["text"])
        except (json.JSONDecodeError, KeyError):
            payload = block.get("text")
if payload is None:
    payload = call.get("structuredContent")

got = payload.get("temperature_c") if isinstance(payload, dict) else None
check(
    "type K 4.096 mV with 25 C terminals returns 124.3 C",
    got is not None and abs(got - 124.31) < 0.05,
    payload,
)

if failures:
    print(f"\n{failures} FAILURE(S)", file=sys.stderr)
    print(proc.stderr[-2000:], file=sys.stderr)
    sys.exit(1)
print("\ncontainer works over stdio with the network switched off")
