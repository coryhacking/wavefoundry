"""Graph, community and derived-output tables inside the shared index database.

Created exactly the way ``sqlite_vector_store.create_schema`` is: DDL only,
inside the CALLER's transaction, never migrating implicitly and never opening
a connection of its own. That is not a stylistic choice — ``sqlite_runtime``'s
module contract forbids opening the shared file with a second SQLite library
in one process, so this module never imports ``sqlite3`` and every connection
it is handed comes from ``sqlite_runtime.connect``.

Identity contract (wave ``1xny6``, change ``1xny5-ref``):

* ``graph_nodes`` is keyed by the existing PUBLIC symbol id. ``row_id`` is a
  private surrogate: writers UPSERT on ``node_id`` so an unchanged public id
  keeps its storage identity across an unrelated edit, and nothing outside
  this database may depend on a surrogate value.
* ``graph_edges`` is keyed by stable source ownership (``source_file``) plus
  the FULL evidence identity (source/target/relation/confidence/evidence)
  plus an ``occurrence`` discriminator. Repeated evidence is preserved: an
  edge triple alone is deliberately NOT a unique storage identity, so two
  identical call sites in one file remain two rows.
* ``graph_file_state`` holds per-file extraction state keyed by the
  normalized repo-relative path; ``graph_merge_state`` holds NAMED merge
  fragments keyed per file, never one whole-corpus blob.
* ``graph_communities`` / ``graph_community_members`` / ``graph_analysis``
  carry the ``input_fingerprint`` they were computed from. Membership is
  diffed by ``(node_id, community_id)`` so an unchanged member is not
  rewritten.
* ``graph_symbol_chunks`` links symbols to canonical chunks by real overlap
  or hash evidence. Zero, one and many links are all legal — there is no
  UNIQUE on ``node_id``, no NOT NULL obligation to exist, and no foreign key
  that would force a chunk row to exist. It stores NO chunk text: canonical
  text stays in ``chunks_<layer>``.
* External endpoints need no owned declaration row: ``graph_edges.target_id``
  is plain text with no foreign key into ``graph_nodes``.
"""
from __future__ import annotations

# Tables this module owns. Exported so the publication transaction can do
# scoped DELETEs (the replacement for the old whole-store reset) without
# re-listing table names at the call site.
GRAPH_TABLES = (
    "graph_nodes",
    "graph_edges",
    "graph_file_state",
    "graph_merge_state",
    "graph_communities",
    "graph_community_members",
    "graph_analysis",
    "graph_symbol_chunks",
)

# Derived-output and per-layer publication bookkeeping created alongside the
# graph tables. Neither is graph content: the map receipt is a derived-output
# receipt and ``build_layer_state`` is per-layer publication state. They are
# listed separately so a graph reset never touches them.
DERIVED_TABLES = (
    "codebase_map_receipt",
    "build_layer_state",
)


def create_schema(conn) -> None:
    """Create the graph + derived tables inside the caller's transaction.

    Mirrors ``sqlite_vector_store.create_schema``: idempotent ``IF NOT
    EXISTS`` DDL, no ``BEGIN``/``COMMIT``, no implicit migration.
    """
    # --- Nodes: public symbol id is the key; row_id is private. ---
    conn.execute("""CREATE TABLE IF NOT EXISTS graph_nodes (
        row_id INTEGER PRIMARY KEY,
        node_id TEXT NOT NULL UNIQUE,
        label TEXT NOT NULL DEFAULT '',
        kind TEXT NOT NULL DEFAULT '',
        source_file TEXT NOT NULL DEFAULT '',
        source_location TEXT NOT NULL DEFAULT '',
        layer TEXT NOT NULL DEFAULT '',
        external INTEGER NOT NULL DEFAULT 0,
        attributes TEXT NOT NULL DEFAULT '{}')""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_source_file "
                 "ON graph_nodes (source_file)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_kind "
                 "ON graph_nodes (kind)")

    # --- Edges: source ownership + full evidence identity + occurrence. ---
    # No foreign key on target_id: an external endpoint (a call into a
    # third-party package) is a legitimate target with no owned declaration.
    conn.execute("""CREATE TABLE IF NOT EXISTS graph_edges (
        row_id INTEGER PRIMARY KEY,
        source_file TEXT NOT NULL,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        relation TEXT NOT NULL,
        confidence TEXT NOT NULL DEFAULT '',
        evidence TEXT NOT NULL DEFAULT '',
        self_edge_kind TEXT NOT NULL DEFAULT '',
        occurrence INTEGER NOT NULL DEFAULT 0,
        attributes TEXT NOT NULL DEFAULT '{}',
        UNIQUE (source_file, source_id, target_id, relation, confidence,
                evidence, occurrence))""")
    # Outgoing and incoming relation lookups are the two serving traversals.
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_outgoing "
                 "ON graph_edges (source_id, relation)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_incoming "
                 "ON graph_edges (target_id, relation)")
    # Per-file retirement (a removed/renamed file drops exactly its rows).
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_source_file "
                 "ON graph_edges (source_file)")

    # --- Per-file extraction state, keyed by normalized path. ---
    conn.execute("""CREATE TABLE IF NOT EXISTS graph_file_state (
        path TEXT PRIMARY KEY,
        layer TEXT NOT NULL DEFAULT '',
        source_hash TEXT NOT NULL DEFAULT '',
        record BLOB,
        extracted_at REAL)""")

    # --- Named merge state, keyed PER FILE (never one corpus-wide blob). ---
    conn.execute("""CREATE TABLE IF NOT EXISTS graph_merge_state (
        path TEXT NOT NULL,
        name TEXT NOT NULL,
        fragment BLOB NOT NULL,
        PRIMARY KEY (path, name))""")

    # --- Communities and derived analysis, bound to their input fingerprint. ---
    conn.execute("""CREATE TABLE IF NOT EXISTS graph_communities (
        community_id TEXT NOT NULL,
        layer TEXT NOT NULL DEFAULT '',
        input_fingerprint TEXT NOT NULL DEFAULT '',
        label TEXT NOT NULL DEFAULT '',
        seed_node_id TEXT NOT NULL DEFAULT '',
        node_count INTEGER NOT NULL DEFAULT 0,
        attributes TEXT NOT NULL DEFAULT '{}',
        PRIMARY KEY (community_id, layer))""")
    # Membership is diffed by (node_id, community_id): an unchanged member
    # keeps its row, so a small delta does not rewrite the whole membership.
    conn.execute("""CREATE TABLE IF NOT EXISTS graph_community_members (
        node_id TEXT NOT NULL,
        community_id TEXT NOT NULL,
        layer TEXT NOT NULL DEFAULT '',
        input_fingerprint TEXT NOT NULL DEFAULT '',
        PRIMARY KEY (node_id, community_id))""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_community_members_community "
                 "ON graph_community_members (community_id)")
    conn.execute("""CREATE TABLE IF NOT EXISTS graph_analysis (
        kind TEXT NOT NULL,
        layer TEXT NOT NULL DEFAULT '',
        input_fingerprint TEXT NOT NULL DEFAULT '',
        method TEXT NOT NULL DEFAULT '',
        payload BLOB NOT NULL,
        computed_at REAL,
        PRIMARY KEY (kind, layer))""")

    # --- Symbol -> canonical chunk links: zero / one / many, evidence-bound. ---
    conn.execute("""CREATE TABLE IF NOT EXISTS graph_symbol_chunks (
        node_id TEXT NOT NULL,
        table_name TEXT NOT NULL,
        chunk_id TEXT NOT NULL,
        evidence TEXT NOT NULL DEFAULT '',
        overlap_lines INTEGER,
        chunk_hash TEXT NOT NULL DEFAULT '',
        PRIMARY KEY (node_id, table_name, chunk_id))""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_symbol_chunks_chunk "
                 "ON graph_symbol_chunks (table_name, chunk_id)")

    # --- Codebase-map receipt: rendered inputs bound to what they describe. ---
    # Written only AFTER the map output is published; recording it never
    # advances the index generation.
    conn.execute("""CREATE TABLE IF NOT EXISTS codebase_map_receipt (
        layer TEXT PRIMARY KEY,
        input_fingerprint TEXT NOT NULL DEFAULT '',
        graph_input_fingerprint TEXT NOT NULL DEFAULT '',
        community_input_fingerprint TEXT NOT NULL DEFAULT '',
        graph_generation INTEGER NOT NULL DEFAULT 0,
        rendered_at REAL)""")

    # --- Per-layer publication state. ---
    # The scalar build_state.generation remains THE reader token consumed by
    # build_epoch_token / build_epoch_state_token; this table records which
    # generation and attempt each layer was last published under.
    conn.execute("""CREATE TABLE IF NOT EXISTS build_layer_state (
        layer TEXT PRIMARY KEY,
        generation INTEGER NOT NULL DEFAULT 0,
        attempt_id TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT '',
        updated_at REAL)""")
