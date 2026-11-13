"""Read private course data into memory; never expose a public file route."""
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


async def load_blob_corpus(path, *, download=download_private_blob):
    if not re.fullmatch(r'(?:courses/)?[a-zA-Z0-9_-]+\.jsonl\.gz\.b64', path):
        raise ValueError('Use a private course Blob pathname, not an arbitrary URL')
    return decode_corpus(await download(path), compressed=True)
