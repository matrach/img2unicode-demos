import asyncio
from pathlib import Path
import re
import socket
import threading
import time

import telnetlib3

HOST = ''
PORT = 51234


TAUNTS = [
    "Yo terminal so dumb, it may not be a terminal at all!",
    "Yo terminal so dumb, it cannot talk basic ANSI codes!",
    "Yo terminal so dumb, it desn't know what a cursor is!",
    "Yo terminal so dumb, it even fakes window size!",
]

files = list(sorted(Path('bbb').glob('*.txt')))
W, H = 118, 32
DIVIDER = .5
FPS = 15 / DIVIDER
SPF = 1. / FPS


async def consume_escape(reader, raw=False):
    full_buf = ''
    buf = ''
    start_found = False
    while True:
        data = await reader.read(10)
        if not data:
            return ''
        full_buf += data
        for read in data:
            if not read:
                return
            if not start_found:
                start_found = read == '\x1b'
            if start_found:
                buf += read
            if 0x40 <= ord(read) <= 0x7e and read != '[':
                if raw:
                    return full_buf
                else:
                    return buf


async def stream(reader, writer, h, w):
    fps = FPS
    rate = 0.
    skipped = 0

    i = 0
    while i < len(files):
        start = time.time()
        # Reset cursor to top=left
        writer.write('\x1b[0;0H')
        frame_data = files[int(i)].read_text().strip().replace('\n', '\r\n')
        writer.writelines(frame_data)
        # Request response after drawing
        writer.write('\x1b[6n')
        await writer.drain()
        # Synchronously wait for response
        # Terminals can in fact consume 200Mbs throgh frame skipping
        # On the other hand, here we are limited by ping latency

        inp = ''  # await consume_escape(reader, raw=True)
        end = time.time()
        diff = end - start
        frames_to_skip = max(1 - i % 1, diff / SPF)
        delay = max(0, SPF - diff)
        fps = min(FPS, .8 * fps + .2 / diff)
        rate = .8 * rate + .2 * fps * len(frame_data.encode())
        # print(len(inp), inp.replace('\x1b', '^['), ":".join("{:02x}".format(ord(c)) for c in inp))
        # print(inp.replace('\x1b', '^['), frames_to_skip, delay)

        skipped += frames_to_skip - 1
        if h > H:
            writer.write(
                f'\r\n[0mCur frame: {int(i): 5d}   FPS: {fps: 3.2f} (synchronous)  bitrate: {int(8 * rate // 1024): 6d} kbps  skipped frames: {int(skipped): 5d}')
        i += frames_to_skip
        if 'q' in inp or 'Q' in inp:
            break
        if delay > 0:
            await asyncio.sleep(delay)

    return '| Thanks for watching! |'


async def test_terminal(reader, writer):
    try:
        garbage = await asyncio.wait_for(reader.read(100), timeout=0.1)
    except asyncio.TimeoutError:
        pass
    else:
        print("garbage:", ":".join("{:02x}".format(ord(c)) for c in garbage))

    writer.write('\x1b[6n')

    try:
        term_resp = await asyncio.wait_for(consume_escape(reader), timeout=0.5)
    except asyncio.TimeoutError:
        term_resp = ''
    print(len(term_resp), term_resp.replace('\x1b', '^['), ":".join("{:02x}".format(ord(c)) for c in term_resp))
    if term_resp != '\x1b[1;1R' and term_resp != '\x1b[0;0R':
        message = f"| {TAUNTS[1]} |"
    else:
        writer.write(f'\x1b[{H + 10};{W + 10}H\x1b[6n')  # set position and query it
        try:
            term_resp = await asyncio.wait_for(consume_escape(reader), timeout=0.5)
        except asyncio.TimeoutError:
            term_resp = ''
        print(len(term_resp), term_resp.replace('\x1b', '^['), ":".join("{:02x}".format(ord(c)) for c in term_resp))
        match = re.search(r'\[(\d+);(\d+)R', term_resp, )
        if match:
            h, w = int(match.group(1)), int(match.group(2))
        else:
            h, w = 0, 0

        if w == 0 and h == 0:
            message = f"| {TAUNTS[2]} |"
        elif w < W or h < H:
            message = f"| Your need at least {W}x{H} terminal, but you have {w}x{h} |"
        else:
            message = h, w
    return message


async def shell(reader, writer):
    print('Connected.', writer._transport.get_extra_info("peername"))
    message = 'An exception occured!'

    writer.write('\x1b7')
    writer.write('\x1b[?1049h')
    writer.write('\x1b[2J')
    writer.write('\x1b[?25l')
    writer.write('\x1b[0;0H')

    try:
        message = await test_terminal(reader, writer)
        if not isinstance(message, str):
            message = await stream(reader, writer, *message)
    except:
        message = 'An exception occured!'
        raise
    finally:
        writer.write('\x1b[?1049l')
        writer.write('\x1b[?25h')
        writer.write('\x1b8')
        if message:
            message = '%s\r\n%s\r\n%s\r\n' % ('-' * len(message), message, '-' * len(message))
        writer.write(message)
        await writer.drain()
        writer.close()
    print('%s bye!' % writer)


loop = asyncio.get_event_loop()
coro = telnetlib3.create_server(port=PORT, host=HOST, shell=shell)
server = loop.run_until_complete(coro)
loop.run_until_complete(server.wait_closed())
