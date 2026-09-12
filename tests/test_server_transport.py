from __future__ import annotations

import io
import unittest

from src.server_transport import LengthPrefixedCodec


class ServerTransportTests(unittest.TestCase):
    def test_codec_round_trip(self):
        payload = b'{"ok":true}'
        stream = io.BytesIO(len(payload).to_bytes(4, "big") + payload)
        self.assertEqual(LengthPrefixedCodec.read(stream), payload)

    def test_codec_rejects_oversized_frame(self):
        stream = io.BytesIO((LengthPrefixedCodec.MAX_FRAME + 1).to_bytes(4, "big"))
        with self.assertRaises(ValueError):
            LengthPrefixedCodec.read(stream)

    def test_codec_rejects_incomplete_frame(self):
        stream = io.BytesIO((5).to_bytes(4, "big") + b"x")
        with self.assertRaises(ConnectionError):
            LengthPrefixedCodec.read(stream)

    def test_codec_rejects_empty_write(self):
        with self.assertRaises(ValueError):
            LengthPrefixedCodec.write(io.BytesIO(), b"")


if __name__ == "__main__":
    unittest.main()
