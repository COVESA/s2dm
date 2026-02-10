# Doks

Doks is a documentation theme for [Thulite](https://thulite.io/).

## Demo

- [doks.netlify.app](https://doks.netlify.app/)

## Install

The recommended way to install the latest version of Doks is by running the command below:

```bash
npm create thulite@latest -- --template doks
```

Looking for help? Start with our [Getting Started](https://getdoks.org/docs/start-here/getting-started/) guide.

## Documentation

Visit our [official documentation](https://getdoks.org/).

## S2DM docs site (local dev, build, deploy)

This repository uses Doks to build the S2DM documentation site in this folder.

### Prerequisites
- Hugo (extended) installed
- Node.js + npm installed

### Install dependencies
```bash
cd docs-gen
npm install
```

### Run local dev server
Standard local server:
```bash
hugo server -D -s ./docs-gen
```

SAFER METHOD: You need local URLs to match production (GitHub Pages under /s2dm/):
```bash
hugo server -D -s ./docs-gen --baseURL http://localhost:1313/s2dm/ --appendPort=false
```

### Build production site locally
```bash
hugo --gc --minify -s ./docs-gen
```
Output is generated in docs-gen/public/.

### Deploy to GitHub Pages
Deployments are handled by the GitHub Actions workflow on main: .github/workflows/docgen.yml.
Push to main to trigger a build and deploy.

## Support

Having trouble? Get help in the official [Doks Discussions](https://github.com/thuliteio/doks/discussions).

## Contributing

New contributors welcome! Check out our [Contributor Guides](https://getdoks.org/contribute/) for help getting started.

## Links

- [License (MIT)](LICENSE)
- [Code of Conduct](https://github.com/thuliteio/.github/blob/main/CODE_OF_CONDUCT.md)
- [Project Funding](.github/FUNDING.md)
- [Website](https://getdoks.org/)

## Sponsors

Doks is free, open source software made possible by Netlify, Algolia, and several other amazing organizations and inidviduals. [Sponsor Doks](.github/FUNDING.md) ❤️
