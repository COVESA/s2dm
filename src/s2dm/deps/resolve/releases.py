from dataclasses import dataclass

from s2dm.deps.models import DependencyMetadata, ProviderRelease, ReleaseAsset, ReleasePage, ReleaseSummary
from s2dm.deps.resolve.common import METADATA_FILENAME, SCHEMA_FILENAME
from s2dm.deps.resolve.context import ResolverContext
from s2dm.deps.resolve.extractors.factory import ExtractorFactory
from s2dm.deps.resolve.providers.factory import ReleaseProviderFactory
from s2dm.deps.resolve.resolve import build_dependency_schema
from s2dm.deps.resolve.resolvers.remote_resolver import RemoteResolver


@dataclass(frozen=True)
class LoadedRelease:
    """The schema text and metadata of one remote release asset."""

    schema_text: str
    metadata: DependencyMetadata


def list_releases(repository: str, page: int, context: ResolverContext | None) -> ReleasePage:
    """List one page of the published releases of a remote repository.

    Args:
        repository: The repository URL, ``https://<host>/<owner>/<repository>``.
        page: The page number, starting at 1.
        context: The resolver context that supplies the access tokens.

    Returns:
        The releases on the page, without drafts, and the paging state.

    Raises:
        DependencySourceError: When the repository does not exist or needs other credentials.
        DependencyUpstreamError: When the provider fails in any other way.
    """
    provider = ReleaseProviderFactory.create_provider(repository, context)
    provider_page = provider.get_release_page(repository, page)
    releases = [_build_release_summary(provider_release) for provider_release in provider_page.releases]
    return ReleasePage(
        releases=releases,
        page=provider_page.page,
        has_next=provider_page.has_next,
        has_previous=provider_page.has_previous,
        last_page=provider_page.last_page,
    )


def load_release(repository: str, tag: str, artifact: str, context: ResolverContext | None) -> LoadedRelease:
    """Load the schema and metadata of one remote release asset, outside the dependency workspace.

    Args:
        repository: The repository URL, ``https://<host>/<owner>/<repository>``.
        tag: The release tag.
        artifact: The asset name: ``schema.graphql`` or a supported archive.
        context: The resolver context that supplies the access tokens.

    Returns:
        The schema text and the release metadata.

    Raises:
        DependencyArtifactError: When the asset does not hold the expected files.
        DependencySourceError: When the asset cannot be accessed, or the schema is not valid GraphQL.
        DependencyUpstreamError: When the provider fails in any other way.
        ValidationError: When ``metadata.yaml`` does not match the dependency metadata model.
    """
    resolver = RemoteResolver(context)
    resolved_source = resolver.resolve_release_asset(repository, tag, artifact)
    metadata = DependencyMetadata.load(resolved_source.source.metadata_path)
    schema_path = resolved_source.source.schema_path
    build_dependency_schema(schema_path, metadata.name, metadata.version)
    schema_text = schema_path.read_text(encoding="utf-8")
    return LoadedRelease(schema_text=schema_text, metadata=metadata)


def _build_release_summary(provider_release: ProviderRelease) -> ReleaseSummary:
    candidate_assets = _find_candidate_assets(provider_release.assets)
    return ReleaseSummary(
        tag=provider_release.tag,
        name=provider_release.name,
        published_at=provider_release.published_at,
        prerelease=provider_release.prerelease,
        candidate_assets=candidate_assets,
    )


def _find_candidate_assets(assets: list[ReleaseAsset]) -> list[ReleaseAsset]:
    """Return the loadable assets with their sizes.

    The direct schema comes first. The archives follow in the given order.
    """
    archive_assets = [asset for asset in assets if ExtractorFactory.supports(asset.name)]
    asset_names = {asset.name for asset in assets}
    has_direct_shape = SCHEMA_FILENAME in asset_names and METADATA_FILENAME in asset_names
    if not has_direct_shape:
        return archive_assets

    schema_asset = next(asset for asset in assets if asset.name == SCHEMA_FILENAME)
    return [schema_asset, *archive_assets]
