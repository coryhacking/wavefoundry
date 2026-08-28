Error Handling
==============

This guide catalogs the exceptions Driftbeam raises and explains which failures the client retries on your behalf.

Error taxonomy
--------------

Every exception raised by the client derives from DriftbeamError, so a single except clause can catch the whole family.
The taxonomy splits into two branches: ClientError for problems the caller can fix, and ServerError for faults inside the service.
Each error exposes a stable machine-readable code that is safe to branch on, unlike the human-readable message.

Client-side errors
------------------

Client errors are never retried automatically, because resending an invalid request cannot make it valid.
Validation failures list every offending field at once rather than stopping at the first problem.
Authentication errors distinguish an expired credential from a revoked one so that rotation logic can react appropriately.

Server-side errors
------------------

Responses with a 5xx status map to ServerError subclasses and are treated as transient by default.
A bad gateway that persists across many retries usually indicates a deploy in progress rather than a client-side fault.
Server errors carry the upstream status code so that dashboards can distinguish overload from outage.

Retry semantics and backoff
---------------------------

The client retries transient failures using exponential backoff with full jitter, starting at 250 milliseconds.
Only idempotent operations are retried automatically; mutating calls must opt in with an idempotency key.
The retry budget defaults to five attempts, after which the original exception is raised unchanged.

.. code-block:: python

   from driftbeam import Client, RetryPolicy

   client = Client(
       retry=RetryPolicy(
           max_attempts=5,
           base_delay=0.25,
           retry_post=False,
       )
   )

Rate limiting
-------------

When the service responds with status 429, the client honors the Retry-After header before scheduling the next attempt.
Sustained throttling is a capacity signal; prefer raising your rate tier over widening client-side retries.

.. note::

   Retry-After values above two minutes are treated as a hard stop, and the rate limit error is raised immediately.

Inspecting error payloads
-------------------------

Every error carries a request identifier that support can correlate with server-side logs.
Include the error code, the request identifier, and the timestamp when opening a support ticket.

.. code-block:: python

   from driftbeam import DriftbeamError

   try:
       client.jobs.create(payload)
   except DriftbeamError as err:
       log.error("driftbeam call failed", code=err.code, request_id=err.request_id)
