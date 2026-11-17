import { themes as prismThemes } from "prism-react-renderer";
import type { LoadedContent, PropSidebar, PropSidebarItem } from "@docusaurus/plugin-content-docs";
import type { Config, LoadContext, Plugin } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";
import { createRequire } from "module";
import path from "path";
import { fileURLToPath } from "url";

const require = createRequire(import.meta.url);
const sourceDirectory = fileURLToPath(new URL("./src", import.meta.url));
const sharedUiDirectory = path.join(sourceDirectory, "shared-ui");
const insightsUiDirectory = path.join(sourceDirectory, "insights-ui");
const ledgerUiDirectory = path.join(sourceDirectory, "ledger-ui");
const searchUiDirectory = path.join(sourceDirectory, "search-ui");

function addBaseUrl(href: string, baseUrl: string): string {
  return href.startsWith("/") ? `${baseUrl}${href.slice(1)}` : href;
}

function addBaseUrlToSidebar(items: PropSidebar, baseUrl: string): PropSidebar {
  return items.map((item): PropSidebarItem => {
    if (item.type === "link") {
      return { ...item, href: addBaseUrl(item.href, baseUrl) };
    }
    if (item.type === "category") {
      return {
        ...item,
        ...(item.href && { href: addBaseUrl(item.href, baseUrl) }),
        items: addBaseUrlToSidebar(item.items, baseUrl),
      };
    }
    return item;
  });
}

function getSidebarLinks(items: PropSidebar): string[] {
  return items.flatMap((item) => {
    if (item.type === "link") {
      return [item.href];
    }
    if (item.type === "category") {
      return getSidebarLinks(item.items);
    }
    return [];
  });
}

/** A page whose routes come from the links of its own sidebar. */
type ContentPage = {
  /** The sidebar's name in `sidebars.ts`. */
  sidebar: string;
  /** The name of the data file that holds the sidebar for the page. */
  data: string;
  /** The address of the page. */
  root: string;
  /** The page component. */
  component: string;
  /** The component of each link route. It renders inside `component`. */
  childComponent?: string;
};

const CONTENT_PAGES: ContentPage[] = [
  {
    sidebar: "insightsSidebar",
    data: "insights-sidebar.json",
    root: "/insights",
    component: "@site/src/insights/InsightsPage.tsx",
  },
  {
    sidebar: "ledgerSidebar",
    data: "ledger-sidebar.json",
    root: "/ledger",
    component: "@site/src/ledger/LedgerPage.tsx",
  },
  {
    sidebar: "releasesSidebar",
    data: "releases-sidebar.json",
    root: "/releases",
    component: "@site/src/releases/ReleasesPage.tsx",
    childComponent: "@site/src/releases/ReleaseSchema.tsx",
  },
];

/**
 * Adds the routes of the content pages. Each page gets one route per link of its sidebar.
 * The sidebar then highlights the current link, as the docs sidebar does.
 * Without `childComponent`, each link route renders `component`.
 * With `childComponent`, `component` renders once at `root`. Each link route then renders
 * `childComponent` inside it, and the sidebar stays in place.
 * A sidebar without links gets one route at `root`, which renders `component`.
 */
const contentPagesPlugin = ({ baseUrl }: LoadContext) => ({
  name: "s2dm-content-pages",
  async allContentLoaded({ allContent, actions }) {
    const docsContent = allContent["docusaurus-plugin-content-docs"]?.default as LoadedContent | undefined;
    const version = docsContent?.loadedVersions.find((candidate) => candidate.isLast);

    for (const page of CONTENT_PAGES) {
      const sidebarItems = version?.sidebars[page.sidebar] as PropSidebar | undefined;
      if (!sidebarItems) {
        throw new Error(`The ${page.sidebar} definition is missing from sidebars.ts`);
      }

      const sidebar = addBaseUrlToSidebar(sidebarItems, baseUrl);
      const sidebarData = await actions.createData(page.data, sidebar);
      const sidebarLinks = getSidebarLinks(sidebar);
      const rootPath = addBaseUrl(page.root, baseUrl);
      if (sidebarLinks.length === 0) {
        actions.addRoute({
          path: rootPath,
          component: page.component,
          exact: true,
          modules: { sidebar: sidebarData },
        });
        continue;
      }
      const childComponent = page.childComponent;
      if (childComponent) {
        const childRoutes = sidebarLinks.map((path) => ({
          path,
          component: childComponent,
          exact: true,
        }));
        actions.addRoute({
          path: rootPath,
          component: page.component,
          exact: false,
          modules: { sidebar: sidebarData },
          routes: childRoutes,
        });
        continue;
      }
      for (const path of sidebarLinks) {
        actions.addRoute({
          path,
          component: page.component,
          exact: true,
          modules: { sidebar: sidebarData },
        });
      }
    }
  },
  configureWebpack(_config, isServer) {
    return {
      resolve: {
        alias: {
          "@": sourceDirectory,
          "@shared-ui": sharedUiDirectory,
          "@insights-ui": insightsUiDirectory,
          "@ledger-ui": ledgerUiDirectory,
          "@search-ui": searchUiDirectory,
          // The server build only pre-renders pages and never runs the embedding
          // worker. The Node build of transformers points at ONNX runtime files
          // that the package does not ship.
          ...(isServer ? { "@huggingface/transformers": false } : {}),
        },
      },
    };
  },
  configurePostCss(options) {
    options.plugins.push(require("@tailwindcss/postcss"));
    return options;
  },
}) satisfies Plugin;

const config: Config = {
  title: "$project_title",
  markdown: { mermaid: true },
  themes: ["@docusaurus/theme-mermaid"],
  future: { v4: true },
  url: "$pages_origin",
  baseUrl: "$pages_base_url",
  organizationName: "$org_name",
  projectName: "$project_name",
  onBrokenLinks: "throw",
  clientModules: [require.resolve("./src/clientModules/markLinkedHeading.ts")],
  i18n: { defaultLocale: "en", locales: ["en"] },
  presets: [[
    "classic",
    {
      docs: { sidebarPath: "./sidebars.ts" },
      blog: false,
      theme: { customCss: "./src/css/custom.css" },
    } satisfies Preset.Options,
  ]],
  themeConfig: {
    image: "img/docusaurus-social-card.jpg",
    colorMode: { defaultMode: "light", disableSwitch: true },
    navbar: {
      title: "$project_title",
      items: [
        { type: "docSidebar", sidebarId: "docsSidebar", position: "left", label: "Docs" },
        { to: "/releases", label: "Releases", position: "left" },
        { to: "/visualizer", label: "Visualizer", position: "left" },
        { to: "/insights", label: "Insights", position: "left" },
        { to: "/ledger", label: "Ledger", position: "left" },
        { href: "$github_repo_url", label: "GitHub", position: "right" },
      ],
    },
    footer: {
      style: "dark",
      links: [{ title: "More", items: [{ label: "GitHub", href: "$github_repo_url" }] }],
      copyright: `Copyright © ${new Date().getFullYear()} $project_title contributors. Website built with <a href="https://docusaurus.io">🦖 Docusaurus</a>.`,
    },
    prism: { theme: prismThemes.github, darkTheme: prismThemes.dracula },
  } satisfies Preset.ThemeConfig,
  plugins: [contentPagesPlugin, [
    "@graphql-markdown/docusaurus",
    {
      schema: "../dist/model.graphql",
      rootPath: "./docs",
      baseURL: "elements",
      formatter: require.resolve("./custom-mdx.cjs"),
      loaders: { GraphQLFileLoader: { module: "@graphql-tools/graphql-file-loader" } },
    },
  ]],
};

export default config;
