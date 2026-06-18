"""Minimal WebSocket server for browser-based Bobo Desktop development.

Usage: python3 -m bobo_tui_gateway.ws_server [port]

This is a dev-only transport. Production uses stdin/stdout (TUI) or
Electron IPC (Desktop App). No new dependencies — uses only stdlib.
"""

import asyncio
import json
import os
import signal
import sys
from http import HTTPStatus

# ── Minimal async HTTP/WS server using only stdlib ──────────────────────

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


class WebSocket:
    """Minimal WebSocket implementation (RFC 6455, text frames only)."""
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.closed = False

    @classmethod
    async def from_handshake(cls, reader, writer):
        request = await reader.readuntil(b'\r\n\r\n')
        key = None
        for line in request.decode().split('\r\n'):
            if line.lower().startswith('sec-websocket-key:'):
                key = line.split(':', 1)[1].strip()
                break
        if not key:
            return None

        import hashlib, base64
        accept = base64.b64encode(
            hashlib.sha1(key.encode() + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest()
        ).decode()

        response = (
            'HTTP/1.1 101 Switching Protocols\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            f'Sec-WebSocket-Accept: {accept}\r\n'
            '\r\n'
        )
        writer.write(response.encode())
        await writer.drain()
        return cls(reader, writer)

    async def recv_text(self):
        while not self.closed:
            header = await self.reader.readexactly(2)
            opcode = header[0] & 0x0f
            if opcode == 0x8:  # close
                self.closed = True
                return None
            if opcode == 0x9:  # ping
                self.writer.write(b'\x8a\x00')
                await self.writer.drain()
                continue
            if opcode != 0x1:  # not text
                continue
            masked = header[1] & 0x80
            length = header[1] & 0x7f
            if length == 126:
                length = int.from_bytes(await self.reader.readexactly(2), 'big')
            elif length == 127:
                length = int.from_bytes(await self.reader.readexactly(8), 'big')
            mask_key = await self.reader.readexactly(4) if masked else None
            data = await self.reader.readexactly(length)
            if mask_key:
                data = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))
            return data.decode()

    async def send_text(self, text):
        data = text.encode()
        frame = bytearray()
        frame.append(0x81)  # text, FIN
        if len(data) < 126:
            frame.append(len(data))
        elif len(data) < 65536:
            frame.append(126)
            frame.extend(len(data).to_bytes(2, 'big'))
        else:
            frame.append(127)
            frame.extend(len(data).to_bytes(8, 'big'))
        frame.extend(data)
        self.writer.write(bytes(frame))
        await self.writer.drain()

    async def close(self):
        self.closed = True
        self.writer.write(b'\x88\x00')
        await self.writer.drain()
        self.writer.close()


async def handle_client(reader, writer):
    ws = await WebSocket.from_handshake(reader, writer)
    if not ws:
        writer.close()
        return

    # Monkey-patch transport.write_json to route events to WebSocket.
    # Engine emits events via _emit() → write_json() in a background thread.
    # Capture the event loop NOW (main thread) — asyncio.get_event_loop()
    # fails in background threads on Python 3.10+.
    import bobo_tui_gateway.transport as transport
    _original_write = transport.write_json
    _loop = asyncio.get_event_loop()
    def _ws_write(msg):
        data = json.dumps(msg, ensure_ascii=False)
        _loop.call_soon_threadsafe(
            lambda d=data: asyncio.ensure_future(ws.send_text(d))
        )
        return True
    transport.write_json = _ws_write

    from bobo_tui_gateway.server import dispatch
    from bobo_tui_gateway.entry import resolve_skin

    # Send gateway.ready
    await ws.send_text(json.dumps({
        "jsonrpc": "2.0", "method": "event",
        "params": {"type": "gateway.ready", "payload": {"skin": resolve_skin()}}
    }, ensure_ascii=False))

    try:
        while not ws.closed:
            text = await ws.recv_text()
            if text is None:
                break
            req = json.loads(text)
            resp = dispatch(req)
            if resp is not None:
                await ws.send_text(json.dumps(resp, ensure_ascii=False))
    finally:
        transport.write_json = _original_write
        await ws.close()


async def main(port=9876):
    server = await asyncio.start_server(handle_client, '127.0.0.1', port)
    print(f'[ws_server] Listening on ws://127.0.0.1:{port}')

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: server.close())
        except NotImplementedError:
            pass

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9876
    asyncio.run(main(port))
