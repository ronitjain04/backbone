"""Read private course data into memory; never expose a public file route."""
import asyncio
import httpx
import re
from .retrieval import CORPUS_LIMIT, decode_corpus


async def download_private_blob(path):
    from vercel import blob
    chunks = []
    size = 0
    async with blob.stream_blob(path, access="private") as stream:
        if stream.metadata.size is not None and stream.metadata.size > CORPUS_LIMIT:
            raise ValueError('Course corpus is too large')
        async for chunk in stream:
            size += len(chunk)
            if size > CORPUS_LIMIT:
                raise ValueError('Course corpus is too large')
            chunks.append(chunk)
    return b''.join(chunks)


async def load_blob_corpus(path, *, download=download_private_blob, sleep=asyncio.sleep):
    if not re.fullmatch(r'(?:courses/)?[a-zA-Z0-9_-]+\.jsonl\.gz\.b64', path):
        raise ValueError('Use a private course Blob pathname, not an arbitrary URL')
    for attempt in range(3):
        try:
            raw = await download(path)
            break
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            transient = not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code in (408, 429) or exc.response.status_code >= 500
            if not transient or attempt == 2:
                raise
            await sleep(2 ** attempt)
    return decode_corpus(raw, compressed=True)
