from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from qiskit.providers.backend import BackendV2

from ..models import HardwareConfig

try:
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit_ibm_runtime.fake_provider import FakeProviderForBackendV2
except ImportError:  # pragma: no cover - exercised only when hardware extras missing
    QiskitRuntimeService = None
    FakeProviderForBackendV2 = None


@lru_cache(maxsize=1)
def _fake_provider() -> Any:
    if FakeProviderForBackendV2 is None:
        raise RuntimeError("qiskit-ibm-runtime is required for fake backends.")
    return FakeProviderForBackendV2()


def resolve_backend(name: str, hardware: HardwareConfig | None = None) -> BackendV2:
    if name.startswith("fake_"):
        return _fake_provider().backend(name)

    if QiskitRuntimeService is None:
        raise RuntimeError(
            "qiskit-ibm-runtime is not installed. Install the hardware extra to use IBM backends."
        )

    service_kwargs: dict[str, Any] = {}
    if hardware and hardware.channel:
        service_kwargs["channel"] = hardware.channel
    if hardware and hardware.instance:
        service_kwargs["instance"] = hardware.instance
    if hardware:
        token = os.getenv(hardware.token_env_var)
        if token:
            service_kwargs["token"] = token

    service = QiskitRuntimeService(**service_kwargs) if service_kwargs else QiskitRuntimeService()
    return service.backend(name)


def backend_metadata(backend: BackendV2) -> dict[str, Any]:
    operation_names = []
    if getattr(backend, "operation_names", None):
        operation_names = sorted(list(backend.operation_names))
    coupling_map = getattr(backend, "coupling_map", None)
    if coupling_map is None:
        coupling_edges = 0
    elif hasattr(coupling_map, "get_edges"):
        coupling_edges = len(coupling_map.get_edges())
    else:
        coupling_edges = len(coupling_map)

    return {
        "name": backend.name,
        "num_qubits": getattr(backend, "num_qubits", None),
        "operation_names": operation_names,
        "coupling_edges": coupling_edges,
    }
