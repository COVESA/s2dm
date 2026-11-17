from pydantic import BaseModel, ConfigDict, TypeAdapter


class GitHubReleaseAsset(BaseModel):
    """A release asset as the GitHub API lists it."""

    model_config = ConfigDict(extra="ignore")

    name: str
    url: str
    size: int


class GitHubReleaseResponse(BaseModel):
    """The assets of one release, from the GitHub release-by-tag reply."""

    model_config = ConfigDict(extra="ignore")

    assets: list[GitHubReleaseAsset]


class GitHubRelease(BaseModel):
    """One release, from the GitHub release list reply."""

    model_config = ConfigDict(extra="ignore")

    tag_name: str
    name: str | None
    draft: bool
    prerelease: bool
    published_at: str | None
    assets: list[GitHubReleaseAsset]


GITHUB_RELEASE_LIST_ADAPTER = TypeAdapter(list[GitHubRelease])
