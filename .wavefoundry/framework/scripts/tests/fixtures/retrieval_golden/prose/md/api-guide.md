# API Guide

This guide covers the everyday request patterns for the Driftbeam API: client setup, authentication, pagination, and streaming.

## Getting started

Create a client once at process startup and share it across threads; construction is expensive but the client is thread-safe.
The client connects lazily on the first request, or you can call `connect()` eagerly to validate credentials at startup.

```python
from driftbeam import Client

client = Client(profile="production")
client.connect()
```

## Authentication

The client sends your API key in the Authorization header on every request, using the Bearer scheme.
Scoped tokens let you rotate keys without interrupting live traffic, because two overlapping tokens can be valid at once.
Never embed keys in source control; load them from the environment or a secrets manager.

```bash
export DRIFTBEAM_API_KEY="db_live_0000000000"
```

## Making requests

Resources are exposed as attributes on the client, and each verb returns a typed response object rather than raw JSON.
Timeouts and retries configured on the client apply uniformly to every resource call.

```python
job = client.jobs.create(name="nightly-sync", schedule="0 2 * * *")
status = client.jobs.get(job.id)
```

## Pagination

The API uses cursor-based pagination rather than numbered pages, so results stay consistent while new records are inserted.
Iterate with the auto-paginating iterator instead of managing cursors by hand; it fetches each page lazily.

```python
for job in client.jobs.list(page_size=100):
    process(job)
```

![Cursor pagination flow](images/pagination-flow.png)

## Streaming results

The stream method yields records as they arrive over a single connection.

```python
from driftbeam import Client

client = Client(profile="production")

for record in client.jobs.stream("nightly-sync"):
    if record.kind == "progress":
        report_progress(record.completed, record.total)
    elif record.kind == "result":
        handle_result(record.payload)
    elif record.kind == "heartbeat":
        continue
    else:
        raise ValueError(f"unexpected record kind: {record.kind}")
```

Backpressure is applied automatically when the consumer falls behind.

```python
import json

CHECKPOINT_PATH = "checkpoints/nightly-sync.json"

def load_offset(path):
    try:
        with open(path) as fh:
            return json.load(fh)["offset"]
    except FileNotFoundError:
        return None

def save_offset(path, offset):
    with open(path, "w") as fh:
        json.dump({"offset": offset}, fh)

offset = load_offset(CHECKPOINT_PATH)
for record in client.jobs.stream("nightly-sync", resume_from=offset):
    handle_result(record.payload)
    save_offset(CHECKPOINT_PATH, record.offset)
```

Resume from a checkpoint by passing the last acknowledged offset.

```python
import asyncio

from driftbeam import AsyncClient

async def consume():
    async with AsyncClient(profile="production") as client:
        async for record in client.jobs.stream("nightly-sync"):
            await handle_result(record.payload)

asyncio.run(consume())
```

The asynchronous client exposes the same streaming interface with an async iterator.

```python
from driftbeam import StreamInterrupted

attempts = 0
while attempts < 3:
    try:
        for record in client.jobs.stream("nightly-sync", resume_from=offset):
            handle_result(record.payload)
            offset = record.offset
        break
    except StreamInterrupted:
        attempts += 1
        continue
```

A stream that drops mid-flight raises StreamInterrupted with the last delivered offset attached.

## Shutting down

Call close when the process exits so pooled connections are returned and pending telemetry is flushed.
The client is also a context manager, which guarantees cleanup even when an exception unwinds the stack.

```python
with Client(profile="production") as client:
    client.jobs.create(name="ad-hoc-backfill")
```

> **Note:** Forgetting to close the client can delay interpreter shutdown by up to the read timeout.
