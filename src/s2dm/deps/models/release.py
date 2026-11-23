from pydantic import BaseModel, Field


class ReleaseAsset(BaseModel):
    """A release asset that s2dm can load."""

    name: str = Field(description="Asset file name")
    size: int = Field(description="Asset file size in bytes, as the provider reports it")


class ReleaseSummary(BaseModel):
    """A published release of a remote repository and the assets that s2dm can load from it."""

    tag: str = Field(description="Release tag")
    name: str | None = Field(description="Release title")
    published_at: str | None = Field(description="Publish date and time in ISO 8601")
    prerelease: bool = Field(description="Whether the release is a pre-release")
    candidate_assets: list[ReleaseAsset] = Field(
        description="Assets that s2dm can load: schema.graphql first for the direct shape, then archives"
    )


class ReleasePage(BaseModel):
    """One page of the published releases of a remote repository."""

    releases: list[ReleaseSummary] = Field(description="Published releases on this page")
    page: int = Field(description="Page number, starting at 1")
    has_next: bool = Field(description="Whether a next page exists")
    has_previous: bool = Field(description="Whether a previous page exists")
    last_page: int | None = Field(
        description=(
            "Number of the last page: the current page when no next page exists, "
            "else the last page the provider reports, else null"
        )
    )


class ProviderRelease(BaseModel):
    """A published release as a release provider reports it, with all its assets."""

    tag: str = Field(description="Release tag")
    name: str | None = Field(description="Release title")
    published_at: str | None = Field(description="Publish date and time in ISO 8601")
    prerelease: bool = Field(description="Whether the release is a pre-release")
    assets: list[ReleaseAsset] = Field(description="All assets of the release")


class ProviderReleasePage(BaseModel):
    """One page of the published releases as a release provider reports it."""

    releases: list[ProviderRelease] = Field(description="Published releases on this page, without drafts")
    page: int = Field(description="Page number, starting at 1")
    has_next: bool = Field(description="Whether a next page exists")
    has_previous: bool = Field(description="Whether a previous page exists")
    last_page: int | None = Field(
        description=(
            "Number of the last page: the current page when no next page exists, "
            "else the last page the provider reports, else null"
        )
    )
