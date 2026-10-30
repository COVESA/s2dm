// Puts the search above the docs sidebar tree. The tree keeps its own scrolling below it.
import type { WrapperProps } from "@docusaurus/types";
import type ContentType from "@theme/DocSidebar/Desktop/Content";
import Content from "@theme-original/DocSidebar/Desktop/Content";
import type { ReactNode } from "react";
import { ElementSearchPanel } from "@/components/ElementSearchPanel";

type ContentProps = WrapperProps<typeof ContentType>;

export default function ContentWrapper(props: ContentProps): ReactNode {
	return (
		<>
			<ElementSearchPanel />
			<Content {...props} />
		</>
	);
}
