import type { PropSidebar } from "@docusaurus/plugin-content-docs";
import { DocsSidebarProvider } from "@docusaurus/plugin-content-docs/client";
import {
	HtmlClassNameProvider,
	ThemeClassNames,
} from "@docusaurus/theme-common";
import DocRootLayout from "@theme/DocRoot/Layout";
import Layout from "@theme/Layout";
import type { ReactNode } from "react";

type ContentPageLayoutProps = {
	title: string;
	description: string;
	sidebarName: string;
	sidebar: PropSidebar;
	children: ReactNode;
};

/**
 * Renders a page next to a docs sidebar, with the look of a docs page.
 * An empty sidebar is left out. The page then takes the full width.
 *
 * @param props.title - The page title.
 * @param props.description - The page description for search engines.
 * @param props.sidebarName - The sidebar's name in `sidebars.ts`.
 * @param props.sidebar - The sidebar items.
 * @param props.children - The page content.
 */
export function ContentPageLayout({
	title,
	description,
	sidebarName,
	sidebar,
	children,
}: ContentPageLayoutProps) {
	let sidebarItems: PropSidebar | undefined;
	if (sidebar.length > 0) {
		sidebarItems = sidebar;
	}
	return (
		<HtmlClassNameProvider className={ThemeClassNames.wrapper.docsPages}>
			<Layout title={title} description={description}>
				<HtmlClassNameProvider className={ThemeClassNames.page.docsDocPage}>
					<DocsSidebarProvider name={sidebarName} items={sidebarItems}>
						<DocRootLayout>{children}</DocRootLayout>
					</DocsSidebarProvider>
				</HtmlClassNameProvider>
			</Layout>
		</HtmlClassNameProvider>
	);
}
