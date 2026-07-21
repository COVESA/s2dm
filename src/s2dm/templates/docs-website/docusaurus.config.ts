import { themes as prismThemes } from "prism-react-renderer";
import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";
import { createRequire } from "module";

const require = createRequire(import.meta.url);

const config: Config = {
  title: "$project_title",
  markdown: { mermaid: true },
  themes: ["@docusaurus/theme-mermaid"],
  future: { v4: true },
  url: "$pages_url",
  baseUrl: "/",
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
  plugins: [[
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
