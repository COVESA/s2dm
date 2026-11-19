import { useDocsSidebar } from "@docusaurus/plugin-content-docs/client";
import { useLocation } from "@docusaurus/router";
import useBaseUrl from "@docusaurus/useBaseUrl";
import { type ReactNode, useEffect, useState } from "react";
import { TextEditor } from "@/components/TextEditor";
import { fetchText } from "@/utils/fetchFile";
import { getErrorMessage } from "@/utils/getErrorMessage";
import { findActiveReleaseTag } from "./activeRelease";
import styles from "./releases.module.css";

// `scripts/stage-releases.js` stages each schema at `static/releases/<tag>/schema.graphql`.
const RELEASES_DIRECTORY = "/releases";

type SchemaLoad =
	| { status: "loaded"; schema: string }
	| { status: "failed"; error: string };

/**
 * Shows the schema of the release that the current address names, in a read-only editor.
 * It renders inside the releases layout, which provides the sidebar.
 */
export default function ReleaseSchema(): ReactNode {
	const sidebar = useDocsSidebar();
	const location = useLocation();
	const releasesUrl = useBaseUrl(RELEASES_DIRECTORY);
	const [schemaLoad, setSchemaLoad] = useState<SchemaLoad | null>(null);
	const sidebarItems = sidebar?.items ?? [];
	const tag = findActiveReleaseTag(sidebarItems, location.pathname);
	let schemaUrl: string | null = null;
	if (tag !== null) {
		const releasesRoot = releasesUrl.replace(/\/$/, "");
		const tagSegment = encodeURIComponent(tag);
		schemaUrl = `${releasesRoot}/${tagSegment}/schema.graphql`;
	}

	useEffect(() => {
		if (schemaUrl === null) {
			return;
		}
		const controller = new AbortController();
		fetchText(schemaUrl, { signal: controller.signal })
			.then((schema) => setSchemaLoad({ status: "loaded", schema }))
			.catch((reason: unknown) => {
				if (!controller.signal.aborted) {
					const error = getErrorMessage(reason);
					setSchemaLoad({ status: "failed", error });
				}
			});
		return () => controller.abort();
	}, [schemaUrl]);

	if (tag === null) {
		return null;
	}
	if (schemaLoad === null) {
		return <div className={styles.status}>Loading the schema...</div>;
	}
	if (schemaLoad.status === "failed") {
		return (
			<div className={styles.status} role="alert">
				Unable to load the schema: {schemaLoad.error}
			</div>
		);
	}
	return (
		<div className={styles.editor}>
			<TextEditor
				language={"graphql"}
				value={schemaLoad.schema}
				readOnly
				fullscreenTitle={tag}
				fileName={`${tag}.graphql`}
			/>
		</div>
	);
}
