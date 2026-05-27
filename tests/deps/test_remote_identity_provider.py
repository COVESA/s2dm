from s2dm.deps.models import RemoteIdentityConfig
from s2dm.deps.resolve.providers import RemoteIdentityProvider


def test_remote_identity_provider_resolves_host_wide_token() -> None:
    remote_identity_config = RemoteIdentityConfig.model_validate(
        {
            "identities": [
                {
                    "host": "github.com",
                    "token": "host-token",
                }
            ]
        }
    )
    remote_identity_provider = RemoteIdentityProvider(remote_identity_config)

    token = remote_identity_provider.resolve_token("https://github.com/owner/repo")

    assert token == "host-token"


def test_remote_identity_provider_resolves_scoped_token() -> None:
    remote_identity_config = RemoteIdentityConfig.model_validate(
        {
            "identities": [
                {
                    "host": "github.com",
                    "scope": "owner/repo",
                    "token": "scoped-token",
                }
            ]
        }
    )
    remote_identity_provider = RemoteIdentityProvider(remote_identity_config)

    token = remote_identity_provider.resolve_token("https://github.com/owner/repo")

    assert token == "scoped-token"


def test_remote_identity_provider_prefers_scoped_token_over_host_wide_token() -> None:
    remote_identity_config = RemoteIdentityConfig.model_validate(
        {
            "identities": [
                {
                    "host": "github.com",
                    "token": "host-token",
                },
                {
                    "host": "github.com",
                    "scope": "owner/repo",
                    "token": "scoped-token",
                },
            ]
        }
    )
    remote_identity_provider = RemoteIdentityProvider(remote_identity_config)

    token = remote_identity_provider.resolve_token("https://github.com/owner/repo")

    assert token == "scoped-token"


def test_remote_identity_provider_returns_none_when_no_match_exists() -> None:
    remote_identity_config = RemoteIdentityConfig.model_validate(
        {
            "identities": [
                {
                    "host": "github.com",
                    "scope": "owner/repo",
                    "token": "scoped-token",
                }
            ]
        }
    )
    remote_identity_provider = RemoteIdentityProvider(remote_identity_config)

    token = remote_identity_provider.resolve_token("https://example.com/owner/repo")

    assert token is None
