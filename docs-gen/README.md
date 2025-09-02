# S2DM Documentation Website

This directory contains the Hugo-based documentation website for the **Simplified Semantic Data Modeling (S2DM)** project.

## Theme & Framework

- **Framework**: [Hugo](https://gohugo.io/) static site generator
- **Theme**: [Doks](https://github.com/h-enk/doks) - A modern documentation theme built on Bootstrap 5
- **CSS Framework**: Bootstrap 5 with custom SCSS
- **Icons**:
  - Lucide icons (for index page features)
  - Font Awesome 5.15.3 (site-wide)

## Hugo Version Management

This project uses a specific Hugo version to ensure consistency between local development and production builds:

- **Local development**: Hugo version is specified in `package.json` under `otherDependencies.hugo`
- **CI/CD (GitHub Actions)**: Hugo version is specified in `.github/workflows/docgen.yml` under `HUGO_VERSION`

⚠️ **Important**: These versions must match to ensure consistent builds. If you update one, update the other.

## Directory Structure

```
docs-gen/
├── assets/          # SCSS, JS, and other build assets
├── config/          # Hugo configuration files
│   ├── _default/    # Default configuration
│   ├── production/  # Production overrides
│   └── next/        # Development overrides
├── content/         # Markdown content files
│   ├── _index.md    # Homepage content
│   ├── docs/        # Documentation pages
│   ├── examples/    # Example pages
│   └── tools/       # Tools documentation
├── layouts/         # Hugo template files
│   ├── index.html   # Custom homepage layout
│   └── partials/    # Reusable template components
├── static/          # Static assets (images, files)
│   └── images/      # Image assets
└── ../docs/         # Built site output (publishDir)
```

## Development Commands

All commands should be run from the `docs-gen` directory:

```bash
cd docs-gen
```

### Install Dependencies
```bash
npm install
```

### Development Server
```bash
# Start development server (recommended)
npm run dev

# Start with drafts enabled
npm run dev:drafts
```
The site will be available at `http://localhost:1313`

### Build & Production
```bash
# Build for production
npm run build

# Preview built site locally
npm run preview
```

### Linting & Quality
```bash
# Run all linters
npm run lint

# Individual linters
npm run lint:scripts    # ESLint for JavaScript
npm run lint:styles     # Stylelint for SCSS/CSS
npm run lint:markdown   # Markdownlint for Markdown
```

### Utilities
```bash
# Create new content
npm run create docs/new-page.md

# Clean build artifacts
npm run clean

# Show version info
npm run info
```

## Image Referencing

### Static Images
Place images in `static/images/` and reference them in Markdown:

```markdown
![Alt text](/images/filename.png)
```

### Full-width Images
For full-width images (like the S2DM role diagram), use HTML:

```html
<div class="w-100 my-4">
  <img src="/images/s2dm_role.png" alt="S2DM Role Overview"
       class="img-fluid w-100" style="max-width: 100%; height: auto;">
</div>
```

### Responsive Images
Use Bootstrap classes for responsive behavior:

```html
<img src="/images/example.png" alt="Description" class="img-fluid">
```

## Content & Callouts

### Hugo Shortcodes

The Doks theme provides several useful shortcodes:

#### Callouts
```markdown
{{< callout type="note" >}}
This is a note callout with helpful information.
{{< /callout >}}

{{< callout type="warning" >}}
This is a warning callout for important notices.
{{< /callout >}}

{{< callout type="tip" >}}
This is a tip callout for helpful suggestions.
{{< /callout >}}
```

Available callout types:
- `note` (blue)
- `tip` (green)
- `warning` (yellow)
- `important` (red)

#### Code Blocks
````markdown
```python
# Python code example
def hello_world():
    print("Hello, S2DM!")
```
````

### Front Matter

Standard front matter for content pages:

```yaml
---
title: "Page Title"
description: "Page description for SEO"
lead: "Brief subtitle or lead text"
date: 2025-07-25
lastmod: 2025-07-25
draft: false
weight: 100
---
```

### Homepage Configuration

The homepage (`content/_index.md`) uses special front matter:

```yaml
---
title: "Simplified Semantic Data Modeling"
lead: "An approach for modeling data of multiple domains..."
---
```

## Customization

### Custom Layouts
- `layouts/index.html` - Custom homepage layout with Lucide icons
- `layouts/partials/` - Reusable components

### Styling
- `assets/scss/` - Custom SCSS files
- Bootstrap 5 variables can be overridden in SCSS

### Icons
- **Lucide icons**: Used in homepage feature cards
- **Font Awesome**: Available site-wide via CDN

## Configuration

### Main Config
- `config/_default/hugo.toml` - Core Hugo settings
- `config/_default/params.toml` - Theme parameters
- `config/_default/menus/` - Navigation menus

### Build Settings
- **Output directory**: `../docs` (for GitHub Pages)
- **Base URL**: Configured per environment
- **Minification**: Enabled in production builds

## Common Issues

### Hugo Version Mismatch
If you encounter build differences between local and CI/CD:
1. Check Hugo version in `package.json` (`otherDependencies.hugo`)
2. Check Hugo version in `.github/workflows/docgen.yml` (`HUGO_VERSION`)
3. Ensure both versions match exactly

### Port Already in Use
If port 1313 is busy:
```bash
npm run dev -- --port 1314
```

### Build Errors
Clear cache and rebuild:
```bash
npm run clean
npm install
npm run build
```

### Image Issues
- Ensure images are in `static/images/`
- Use forward slashes in paths: `/images/file.png`
- Check file extensions match exactly
- SVG images might not scale correctly, stick to PNGs

## 📖 Documentation Links

- [Hugo Documentation](https://gohugo.io/documentation/)
- [Doks Theme Guide](https://getdoks.org/)
- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.3/)
- [Lucide Icons](https://lucide.dev/)

---

For questions about the S2DM project itself, see the main repository README.
