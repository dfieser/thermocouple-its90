# Container image for the thermocouple-its90 MCP server.
#
# The server speaks MCP over stdio, so the container attaches to a client
# rather than running as a long-lived service:
#
#     docker build -t thermocouple-its90-mcp .
#     docker run --rm -i thermocouple-its90-mcp
#
# It needs no network, no volumes and no environment variables. Every
# coefficient is compiled into the package, so the container is a pure
# function of its inputs and can run with the network switched off.

FROM python:3.13-slim

# stdio is the MCP transport, so stdout must not be buffered or the
# handshake stalls waiting on a flush that never comes.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Only what the wheel is built from. Tests and docs stay out of the image.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir ".[mcp]"

# Nothing here writes to disk, so drop root.
RUN useradd --create-home --uid 10001 mcp
USER mcp

ENTRYPOINT ["thermocouple-its90-mcp"]
