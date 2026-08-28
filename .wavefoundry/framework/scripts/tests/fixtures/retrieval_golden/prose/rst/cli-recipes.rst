CLI Recipes
===========

Task-oriented command lines for the driftbeam CLI beyond the basics in the installation guide.

Exporting job history
---------------------

The export subcommand writes one line of JSON per completed job and accepts a time window.

.. code-block:: bash

   driftbeam jobs export --since 30d --format ndjson --output history.ndjson

Pruning old artifacts
---------------------

Prune removes artifacts older than the retention window; run it from a scheduled job rather than by hand.

.. code-block:: bash

   driftbeam artifacts prune --keep-days 90 --dry-run

Shell completion
----------------

Completion scripts are generated per shell and sourced from your profile.

.. code-block:: bash

   driftbeam completion zsh > ~/.driftbeam-completion.zsh
