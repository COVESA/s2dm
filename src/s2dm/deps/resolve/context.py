from dataclasses import dataclass

from s2dm.deps.resolve.providers.remote_identity_provider import RemoteIdentityProvider
from s2dm.deps.resolve.warnings import WarningCollector


@dataclass(frozen=True)
class ResolverContext:
    """Runtime services shared across resolver instances."""

    remote_identity_provider: RemoteIdentityProvider | None = None
    warning_collector: WarningCollector | None = None

    def warn(self, message: str) -> None:
        """Emit a dependency-resolution warning if a collector is configured."""
        if self.warning_collector is None:
            return
        self.warning_collector.warn(message)
