from dataclasses import dataclass

from s2dm.deps.resolve.providers.remote_identity_provider import RemoteIdentityProvider


@dataclass(frozen=True)
class ResolverContext:
    """Runtime services shared across resolver instances."""

    remote_identity_provider: RemoteIdentityProvider | None = None
