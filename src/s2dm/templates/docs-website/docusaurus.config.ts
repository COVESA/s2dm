import { themes as prismThemes } from "prism-react-renderer";
import type { LoadedContent, PropSidebar, PropSidebarItem } from "@docusaurus/plugin-content-docs";
import type { Config, LoadContext, Plugin } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";
import { createRequire } from "module";
import { fileURLToPath } from "url";

const require = createRequire(import.meta.url);
const sourceDirectory = fileURLToPath(new URL("./src", import.meta.url));
const insightsUiDirectory = fileURLToPath(new URL("./src/insights-ui", import.meta.url));
const ledgerUiDirectory = fileURLToPath(new URL("./src/ledger-ui", import.meta.url));

function addBaseUrlToSidebar(items: PropSidebar, baseUrl: string): PropSidebar {
  const addBaseUrl = (href: string) =>
    href.startsWith("/") ? `${baseUrl}${href.slice(1)}` : href;

  return items.map((item): PropSidebarItem => {
    if (item.type === "link") {
      return { ...item, href: addBaseUrl(item.href) };
    }
    if (item.type === "category") {
      return {
        ...item,
        ...(item.href && { href: addBaseUrl(item.href) }),
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

// Each workspace renders one page against its own docs sidebar, with a route per
// sidebar link so the sidebar highlights the current view the way the docs do.
const SIDEBAR_PAGES = [
  { sidebar: "insightsSidebar", data: "insights-sidebar.json", component: "@site/src/insights/InsightsPage.tsx" },
  { sidebar: "ledgerSidebar", data: "ledger-sidebar.json", component: "@site/src/ledger/LedgerPage.tsx" },
];

const insightsPlugin = ({ baseUrl }: LoadContext) => ({
  name: "s2dm-insights",
  async allContentLoaded({ allContent, actions }) {
    const docsContent = allContent["docusaurus-plugin-content-docs"]?.default as LoadedContent | undefined;
    const version = docsContent?.loadedVersions.find((candidate) => candidate.isLast);

    for (const page of SIDEBAR_PAGES) {
      const sidebarItems = version?.sidebars[page.sidebar] as PropSidebar | undefined;
      if (!sidebarItems) {
        throw new Error(`The ${page.sidebar} definition is missing from sidebars.ts`);
      }

      const sidebar = addBaseUrlToSidebar(sidebarItems, baseUrl);
      const sidebarData = await actions.createData(page.data, sidebar);
      for (const path of getSidebarLinks(sidebar)) {
        actions.addRoute({
          path,
          component: page.component,
          exact: true,
          modules: { sidebar: sidebarData },
        });
      }
    }
  },
  configureWebpack() {
    return {
      resolve: {
        alias: {
          "@": sourceDirectory,
          "@insights-ui": insightsUiDirectory,
          "@ledger-ui": ledgerUiDirectory,
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
        { type: "docSidebar", sidebarId: "tutorialSidebar", position: "left", label: "Docs" },
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
  plugins: [insightsPlugin, [
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
