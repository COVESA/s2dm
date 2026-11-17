import type { PropSidebar } from "@docusaurus/plugin-content-docs";
import { isActiveSidebarItem } from "@docusaurus/plugin-content-docs/client";

/**
 * Finds the release tag that the current address names.
 *
 * @param sidebar - The releases sidebar. Each link label is a release tag.
 * @param pathname - The current address.
 * @returns The tag, or `null` when no release link matches the address.
 */
export function findActiveReleaseTag(
	sidebar: PropSidebar,
	pathname: string,
): string | null {
	const activeLink = sidebar.find((item) =>
		isActiveSidebarItem(item, pathname),
	);
	if (activeLink?.type !== "link") {
		return null;
	}
	return activeLink.label;
}
