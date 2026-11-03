"""HTTP boundary unit tests plus real loopback SDK/DuckDB integration.

Temporary synthetic fixture only; never a company endpoint or credentials.
"""
import asyncio
from datetime import timedelta
import json
from pathlib import Path
import socket
from threading import Thread
import time

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import stream_within_origin
import pytest
import uvicorn

from data_workspace.source_profiles import ProfileDraft, SourceStore
from data_workspace.warehouse.client import TOOLS
from data_workspace.warehouse.http_boundary import (
    HTTPBoundaryError, HTTPEndpointPolicy, GovernedHTTPTransport,
    checked_endpoint, create_governed_http_client,
)

ENDPOINT = "http://127.0.0.1:19001/mcp"


@pytest.mark.parametrize("endpoint", [
    "http://127.0.0.1:19001/mcp", "http://[::1]:19001/mcp",
    "https://10.32.1.1:443/mcp", "https://8.8.8.8:443/api/mcp",
])
def test_numeric_endpoint_format_without_network(endpoint):
    assert checked_endpoint(endpoint) == endpoint
    assert HTTPEndpointPolicy((endpoint,)).authorize(endpoint) == endpoint


@pytest.mark.parametrize("endpoint", [
    "http://127.0.0.1/mcp", "http://localhost:19001/mcp",
    "http://127.1:19001/mcp", "http://2130706433:19001/mcp",
    "http://127.0.0.1:19001/mcp?token=private-sentinel",
    "http://127.0.0.1:19001/mcp?", "http://127.0.0.1:19001/mcp#",
    "http://user:private-sentinel@127.0.0.1:19001/mcp",
    "http://127.0.0.1:19001/api/../mcp", "http://127.0.0.1:19001/mcp/",
    "http://127.0.0.1:19001//mcp", "http://127.0.0.1:19001/%6dcp",
    "http://127.0.0.1:19001/mcp\\evil", " http://127.0.0.1:19001/mcp",
    "http://127.0.0.1:19001/mcp\n", "http://127.0.0.1:19001/中文",
    "http://10.32.1.1:19001/mcp", "https://169.254.169.254:443/mcp",
    "https://0.0.0.0:443/mcp", "https://224.0.0.1:443/mcp",
    "https://255.255.255.255:443/mcp", "https://[fe80::1]:443/mcp",
    "https://[::ffff:127.0.0.1]:443/mcp", "ftp://127.0.0.1:19001/mcp",
    "http://127.0.0.1:0/mcp", "http://127.0.0.1:99999/mcp",
])
def test_invalid_endpoint_cannot_echo_secrets(endpoint):
    with pytest.raises(HTTPBoundaryError) as caught:
        HTTPEndpointPolicy((endpoint,))
    assert "private-sentinel" not in str(caught.value)
    assert endpoint not in str(caught.value)


def test_server_policy_cannot_be_mutated_by_a_list():
    with pytest.raises(HTTPBoundaryError):
        HTTPEndpointPolicy([ENDPOINT])


def test_default_policy_denies_before_transport_construction():
    with pytest.raises(HTTPBoundaryError):
        create_governed_http_client(ENDPOINT, HTTPEndpointPolicy())


def test_exact_endpoint_no_method_or_header_escalation():
    seen = []
    async def handle(request):
        seen.append(request)
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(200, json={"ok": True})
    async def exercise():
        async with create_governed_http_client(ENDPOINT, HTTPEndpointPolicy((ENDPOINT,)), transport=httpx.MockTransport(handle)) as client:
            assert (await client.post(ENDPOINT, json={})).status_code == 200
            for url, method, headers in [
                (ENDPOINT + "?token=private-sentinel", "POST", {}),
                (ENDPOINT.replace("mcp", "other"), "POST", {}),
                (ENDPOINT, "PUT", {}),
                (ENDPOINT, "POST", {"Host": "other.internal"}),
                (ENDPOINT, "POST", {"X-Forwarded-Host": "other.internal"}),
                (ENDPOINT, "POST", {"Authorization": "Bearer private-sentinel"}),
                (ENDPOINT, "POST", {"Cookie": "secret=private-sentinel"}),
                (ENDPOINT, "POST", {"Proxy-Authorization": "private-sentinel"}),
            ]:
                with pytest.raises(HTTPBoundaryError) as caught:
                    await client.request(method, url, headers=headers)
                assert "private-sentinel" not in str(caught.value)
            with pytest.raises(HTTPBoundaryError):
                await client.post(ENDPOINT, content=b"x" * (65536 + 1))
            assert len(seen) == 1
    asyncio.run(exercise())


def test_https_default_port_normalization_has_no_extra_network_target():
    endpoint = "https://8.8.8.8:443/mcp"
    async def exercise():
        async with create_governed_http_client(endpoint, HTTPEndpointPolicy((endpoint,)), transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))) as client:
            assert (await client.post(endpoint, json={})).status_code == 200
    asyncio.run(exercise())


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_sdk_cannot_follow_even_same_origin_redirect(status):
    seen = []
    responses = []
    def handle(request):
        seen.append(request)
        response = httpx.Response(status, headers={"Location": "/other?token=private-sentinel"}, content=b"private-sentinel")
        responses.append(response)
        return response
    async def exercise():
        async with create_governed_http_client(ENDPOINT, HTTPEndpointPolicy((ENDPOINT,)), transport=httpx.MockTransport(handle)) as client:
            with pytest.raises(HTTPBoundaryError) as caught:
                async with stream_within_origin(client, "POST", ENDPOINT, json={}):
                    pytest.fail("redirect accepted")
            assert "private-sentinel" not in str(caught.value)
            assert len(seen) == 1 and responses[0].is_closed
    asyncio.run(exercise())


class Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False
    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk
    async def aclose(self):
        self.closed = True


@pytest.mark.parametrize("headers", [{"Content-Encoding": "gzip"}, {"Content-Length": "10000000"}, {"Content-Length": "-1"}, {"Content-Length": "private-sentinel"}])
def test_encoded_or_declared_oversized_response_is_closed(headers):
    stream = Chunks([b"private-sentinel"])
    async def exercise():
        async with create_governed_http_client(ENDPOINT, HTTPEndpointPolicy((ENDPOINT,)), transport=httpx.MockTransport(lambda r: httpx.Response(200, headers=headers, stream=stream))) as client:
            with pytest.raises(HTTPBoundaryError) as caught:
                await client.post(ENDPOINT, json={})
            assert "private-sentinel" not in str(caught.value)
            assert stream.closed
    asyncio.run(exercise())


def test_chunked_sse_budget_is_checked_before_sdk_parsing_and_closes():
    stream = Chunks([b"data: " * 5, b"x" * 71])
    async def exercise():
        transport = GovernedHTTPTransport(ENDPOINT, HTTPEndpointPolicy((ENDPOINT,)), transport=httpx.MockTransport(lambda r: httpx.Response(200, stream=stream)), max_response_bytes=100)
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(HTTPBoundaryError):
                await client.post(ENDPOINT, json={})
            assert stream.closed
    asyncio.run(exercise())


def test_real_loopback_http_mcp_handshake_catalog_dates_and_100_rows(tmp_path, monkeypatch):
    from data_workspace.warehouse.mcp_server import create_server
    # The production store is untouched; create a synthetic snapshot in tmp_path.
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    source = allowed / "fixture.csv"
    source.write_text("id,created_at,shipped_on\n" + "".join(f"{i},2025-01-01 12:00:00,2025-01-02\n" for i in range(120)), encoding="utf-8")
    store = SourceStore(tmp_path / "connections", allowed)
    database, _ = store.snapshot(ProfileDraft(name="HTTP fixture", path=str(source), usage_authorized=True))
    mcp_server = create_server(tmp_path, database)
    application = mcp_server.streamable_http_app()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    endpoint = f"http://127.0.0.1:{sock.getsockname()[1]}/mcp"
    # This independent fixture owns live SSE connections; bound their shutdown inside the existing10s thread guard.
    server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", log_level="error", access_log=False, timeout_graceful_shutdown=2))
    thread = Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started, "owned HTTP fixture failed to start"
        # Invalid environment proxies/CA paths must not be consulted.
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            monkeypatch.setenv(name, "http://127.0.0.1:1")
        monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "no-environment-ca.pem"))
        async def exercise():
            async with create_governed_http_client(endpoint, HTTPEndpointPolicy((endpoint,))) as http_client:
                async with streamable_http_client(endpoint, http_client=http_client) as (read, write, _):
                    async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=10)) as session:
                        assert (await session.initialize()).protocolVersion
                        assert {tool.name for tool in (await session.list_tools()).tools} == TOOLS
                        metadata = (await session.call_tool("list_tables", {})).structuredContent["metadata"]
                        assert metadata["source"] == "user_provided" and metadata["tables"][0]["id"] == "t0"
                        receipt = (await session.call_tool("submit_query", {"request": {"table": "t0", "limit": 100}, "idempotency_key": "http-navigation-fixture"})).structuredContent
                        assert receipt["task"]["status"] == "SUCCEEDED"
                        data = (await session.call_tool("get_query_result", {"task_id": receipt["task"]["task_id"]})).structuredContent["result"]
                        assert data["returned_row_count"] == 100 and data["truncated"] is True
                        assert [c["name"] for c in data["columns"]] == ["id", "created_at", "shipped_on"]
                        assert data["rows"][0][1:] == ["2025-01-01T12:00:00", "2025-01-02"]
                        assert data["source"] == "user_provided" and data["currency"] is None
        asyncio.run(asyncio.wait_for(exercise(), timeout=20))
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()
        assert not thread.is_alive(), "owned fixture did not release its HTTP worker"
