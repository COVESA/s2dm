// Puts the search above the docs sidebar tree. The tree keeps its own scrolling below it.
import { useDocsSidebar } from "@docusaurus/plugin-content-docs/client";
import type { WrapperProps } from "@docusaurus/types";
import type ContentType from "@theme/DocSidebar/Desktop/Content";
import Content from "@theme-original/DocSidebar/Desktop/Content";
import type { ReactNode } from "react";
import { ElementSearchPanel } from "@/components/ElementSearchPanel";

type ContentProps = WrapperProps<typeof ContentType>;

// The search finds pages of the docs tab. The other sidebars show their own pages without it.
const DOCS_SIDEBAR_NAME = "docsSidebar";

export default function ContentWrapper(props: ContentProps): ReactNode {
	const sidebar = useDocsSidebar();
	if (sidebar?.name !== DOCS_SIDEBAR_NAME) {
		return <Content {...props} />;
	}
	return (
		<>
			<ElementSearchPanel />
			<Content {...props} />
		</>
	);
}
