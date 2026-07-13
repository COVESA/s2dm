from urllib.parse import urlparse

from s2dm.deps.models import RemoteIdentityConfig


class RemoteIdentityProvider:
    """Resolve remote access tokens from configured identity entries."""

    def __init__(self, remote_identity_config: RemoteIdentityConfig) -> None:
        self.remote_identity_config = remote_identity_config

    def resolve_token(self, repository_url: str) -> str | None:
        """Return the configured token for a remote repository URL, if any."""
        parsed_repository = urlparse(repository_url)
        repository_host = parsed_repository.netloc
        repository_scope = self._resolve_scope(parsed_repository.path)
        host_token: str | None = None

        for identity in self.remote_identity_config.identities:
            if identity.host != repository_host:
                continue
            if identity.scope is None:
                host_token = identity.token
                continue
            if identity.scope == repository_scope:
                return identity.token

        return host_token

    def _resolve_scope(self, repository_path: str) -> str | None:
        path_segments = [path_segment for path_segment in repository_path.split("/") if path_segment]
        if len(path_segments) < 2:
            return None
        return "/".join(path_segments[:2])
