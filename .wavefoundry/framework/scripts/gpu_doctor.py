#!/usr/bin/env python3
"""``wf gpu-doctor`` — embedding-provider / GPU capability diagnostic (wave 1p8gz).

A thin CLI entry that surfaces the SAME diagnostics as the ``wf_gpu_doctor`` MCP tool and the
``setup-wavefoundry --check-gpu`` path — platform, onnxruntime, GPU detection (nvidia/apple),
available ONNX execution providers, the provider Wavefoundry would select (+ reason/remediation),
and the CUDA 12/13 ABI-gap check. It reuses the shared backing logic in ``provider_policy`` (the
single source of GPU/provider detection); this module only formats the result for a terminal. No
detection logic is duplicated here.

Like every other ``wf`` subcommand, this self-bootstraps into the shared tool venv in-process so the
GPU/provider libraries (onnxruntime, etc.) resolve.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Activate the shared tool venv IN-PROCESS so GPU/provider libs resolve (wave 1p7pl/1p802). No-op when
# already in the venv or when it does not exist yet.
venv_bootstrap.activate_tool_venv()
# CLI entry — UTF-8 stdout/stderr so non-ASCII prints never raise on a cp1252 console (wave 1p8gv).
cli_stdio.configure_utf8_stdio()


def main(argv: list[str] | None = None) -> int:
    # No args of our own — accept (and ignore) any forwarded argv for dispatcher symmetry; `-h`/`--help`
    # prints the one-line purpose since the report itself IS the output.
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        print(
            "wf gpu-doctor — embedding-provider / GPU capability diagnostic (read-only). "
            "Same report as the wf_gpu_doctor MCP tool and `setup-wavefoundry --check-gpu`."
        )
        return 0

    import provider_policy
    import setup_index

    # Reuse the SAME backing logic as wf_gpu_doctor_response / setup_wavefoundry._run_gpu_check:
    # provider_policy.diagnostic_report drives detection; setup's bounded probe makes the selected
    # provider match runtime (e.g. CoreML on Apple Silicon). No duplicated detection here.
    report = provider_policy.diagnostic_report(provider_probe=setup_index._probe_embedding_provider)
    print(provider_policy.format_diagnostic_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
