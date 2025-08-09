import io

def encode_base128(n: int) -> bytes:
    """Encode integer into base-128 variable-length quantity (LEB128)."""
    if n < 0:
        raise ValueError("Cannot encode negative numbers in base128")
    out = bytearray()
    while True:
        to_write = n & 0x7F
        n >>= 7
        if n:
            out.append(to_write | 0x80)
        else:
            out.append(to_write)
            break
    return bytes(out)

def decode_base128_stream(stream: io.BufferedReader):
    """Read a base-128 encoded integer from a binary stream.
    Returns (value, bytes_read). If EOF is reached, returns (None, 0)."""
    shift = 0
    result = 0
    bytes_read = 0
    while True:
        b = stream.read(1)
        if not b:
            if bytes_read == 0:
                return None, 0
            raise EOFError("Incomplete base128 sequence")
        byte = b[0]
        bytes_read += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, bytes_read
        shift += 7

def decode_base128(data: bytes) -> int:
    stream = io.BytesIO(data)
    value, consumed = decode_base128_stream(stream)
    if consumed != len(data):
        raise ValueError("Extra bytes after base128 data")
    return value
