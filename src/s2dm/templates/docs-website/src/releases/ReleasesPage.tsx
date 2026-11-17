import type { PropSidebar } from "@docusaurus/plugin-content-docs";
import renderRoutes from "@docusaurus/renderRoutes";
import { useLocation } from "@docusaurus/router";
import type { ReactNode } from "react";
import { ContentPageLayout } from "@/components/ContentPageLayout";
import { findActiveReleaseTag } from "./activeRelease";
import styles from "./releases.module.css";

type ReleasesPageProps = {
	route: { routes?: Parameters<typeof renderRoutes>[0] };
	sidebar: PropSidebar;
};

/**
 * Renders the releases layout once, with the schema of the active release inside.
 * The layout and its sidebar stay mounted while the reader moves between releases.
 * With no releases staged, the page says so and has no sidebar.
 *
 * @param props.route - The route of this page. Its child routes show the schemas.
 * @param props.sidebar - The releases sidebar. Each link label is a release tag.
 */
export default function ReleasesPage({
	route,
	sidebar,
}: ReleasesPageProps): ReactNode {
	const location = useLocation();
	const tag = findActiveReleaseTag(sidebar, location.pathname);

	let content: ReactNode;
	if (sidebar.length === 0) {
		content = (
			<div className={styles.status}>No releases are available.</div>
		);
	} else if (tag === null) {
		content = (
			<div className={styles.status} role="alert">
				This address names no release.
			</div>
		);
	} else {
		content = renderRoutes(route.routes);
	}

	return (
		<ContentPageLayout
			title={"Releases"}
			description={"Schemas of past releases"}
			sidebarName={"releasesSidebar"}
			sidebar={sidebar}
		>
			<article className={styles.content}>{content}</article>
		</ContentPageLayout>
	);
}
