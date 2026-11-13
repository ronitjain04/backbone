"""Read private course data into memory; never expose a public file route."""
import asyncio
import httpx
import httpx2
from vercel.blob.errors import BlobError
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
        except (BlobError, httpx.TransportError, httpx2.TransportError, httpx.HTTPStatusError) as exc:
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else getattr(exc, 'status_code', None)
            transient = isinstance(exc, (httpx.TransportError, httpx2.TransportError)) or isinstance(exc.__cause__, (httpx.TransportError, httpx2.TransportError)) or (status is not None and (status in (408, 429) or status >= 500))
            if not transient or attempt == 2:
                raise
            await sleep(2 ** attempt)
    return decode_corpus(raw, compressed=True)
