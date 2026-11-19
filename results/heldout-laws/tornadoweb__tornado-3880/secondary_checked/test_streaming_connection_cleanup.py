import asyncio
import socket
from unittest.mock import Mock, patch

from tornado import testing
from tornado.httpserver import HTTPServer
from tornado.iostream import IOStream
from tornado.test import circlerefs_test


def test_streaming_callback_teardown_closes_the_accepted_socket():
    """New: The streaming-callback test closes its accepted socket even while the peer close is pending (A1)."""
    peer_socket, accepted_socket = socket.socketpair()

    def add_connected_stream(server, listener):
        server.handle_stream(IOStream(accepted_socket), ("127.0.0.1", 12345))

    class LocalStreamingClient:
        async def fetch(self, url, *, streaming_callback):
            self.stream = IOStream(peer_socket)
            await self.stream.write(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await self.stream.read_until(b"\r\n\r\n")
            streaming_callback(await self.stream.read_bytes(3))

        def close(self):
            # Keep the peer open until the verdict to model delayed peer EOF.
            pass

    chunks = []
    with peer_socket, accepted_socket:
        with (
            patch.object(testing, "bind_unused_port", return_value=(Mock(), 12345)),
            patch.object(HTTPServer, "add_socket", add_connected_stream),
        ):
            asyncio.run(
                circlerefs_test.CircleRefsTest().run_handler(
                    circlerefs_test.OkHandler,
                    client_factory=LocalStreamingClient,
                    streaming_callback=chunks.append,
                )
            )

        assert chunks == [b"ok\n"]
        assert accepted_socket.fileno() == -1
