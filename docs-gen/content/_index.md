---
title:  Simplified Semantic Data Modeling (S2DM)
layout: hextra-home
---

{{< hextra/hero-badge >}}
  <div class="hx:w-2 hx:h-2 hx:rounded-full hx:bg-primary-400"></div>
  <span>Simple & Semantic</span>
  {{< icon name="sparkles" attributes="height=14" >}}
{{< /hextra/hero-badge >}}

<div class="hx:mt-6 hx:mb-6">
{{< hextra/hero-headline >}}
  Simplified Semantic&nbsp;<br class="hx:sm:block hx:hidden" />Data Modeling (S2DM)
{{< /hextra/hero-headline >}}
</div>

<div class="hx:mb-12">
{{< hextra/hero-subtitle >}}
  An approach for modeling data across multiple domains.&nbsp;<br class="hx:sm:block hx:hidden" />Simple for SMEs, semantic for meaningful relationships.
{{< /hextra/hero-subtitle >}}
</div>

<div class="hx:mb-6">
{{< hextra/hero-button text="Get Started" link="1-modeling-guideline" >}}
</div>

<div class="hx:mt-6"></div>

{{< hextra/hero-container cols="2" image="images/s2dm_overview.svg" imageWidth="500" imageHeight="400" >}}

The <em>Simplified Semantic Data Modeling</em> (<code>S2DM</code>) is an approach for modeling data of multiple domains.
It is <strong><em>simple</em></strong> in the sense that any <em>Subject Matter Expert</em> (SME) could contribute to a controlled vocabulary with minimal data modeling expertise.
Likewise, it is <strong><em>semantic</em></strong> in the sense that it specifies meaningful data structures, their cross-domain relationships, and arbitrary classification schemes.

{{< /hextra/hero-container >}}

> [!NOTE]
> Bear in mind the word `Simplified` in the name.
> This approach aims to foster the adoption of (some) good data modeling practices.
> It does not intent to re-invent, nor to replace long-standing standards, such as those of the [Semantic Web](https://www.w3.org/2001/sw/wiki/Main_Page).
> Hence, it does not incorporate advanced reasoning capabilities or comprehensive ontologies typically associated with traditional semantic data modeling.

<div class="hx:mb-8">
{{< hextra/hero-section >}}
S2DM Features
{{< /hextra/hero-section >}}
</div>

{{< hextra/feature-grid >}}
  {{< hextra/feature-card
    title="Simple for SMEs"
    subtitle="Subject Matter Experts can contribute to controlled vocabularies with minimal data modeling expertise."
    class="hx:aspect-auto hx:md:aspect-[1.1/1] hx:max-md:min-h-[340px]"
    style="background: radial-gradient(ellipse at 50% 80%,rgba(34,197,94,0.15),hsla(0,0%,100%,0));"
  >}}
  {{< hextra/feature-card
    title="Semantic Relationships"
    subtitle="Specify meaningful data structures, cross-domain relationships, and arbitrary classification schemes."
    class="hx:aspect-auto hx:md:aspect-[1.1/1] hx:max-lg:min-h-[340px]"
    style="background: radial-gradient(ellipse at 50% 80%,rgba(59,130,246,0.15),hsla(0,0%,100%,0));"
  >}}
  {{< hextra/feature-card
    title="Multiple Domains"
    subtitle="Model data across multiple domains with consistent patterns and reusable components."
    class="hx:aspect-auto hx:md:aspect-[1.1/1] hx:max-md:min-h-[340px]"
    style="background: radial-gradient(ellipse at 50% 80%,rgba(168,85,247,0.15),hsla(0,0%,100%,0));"
  >}}
{{< /hextra/feature-grid >}}

<div class="hx:mb-8">
{{< hextra/hero-section >}}
S2DM Artifacts
{{< /hextra/hero-section >}}
</div>

S2DM consists of two main artifacts:

{{< hextra/feature-grid cols="2" >}}
  {{< hextra/feature-card
    title="Data Modeling Guideline"
    subtitle="Learn how to formalize the data of a domain with the S2DM approach. Create specification files that constitute the core of the conceptual/logical layer."
    class="hx:aspect-auto hx:md:aspect-[1.1/1] hx:max-md:min-h-[240px]"
    style="background: radial-gradient(ellipse at 50% 80%,rgba(249,115,22,0.15),hsla(0,0%,100%,0));"
  >}}
  {{< hextra/feature-card
    title="S2DM Tools"
    subtitle="Code that supports the proper usage of the S2DM data modeling guideline. Includes validation, identifiers, search functions, exporters, and more."
    class="hx:aspect-auto hx:md:aspect-[1.1/1] hx:max-md:min-h-[240px]"
    style="background: radial-gradient(ellipse at 50% 80%,rgba(236,72,153,0.15),hsla(0,0%,100%,0));"
  >}}
{{< /hextra/feature-grid >}}

<div class="hx:mb-8">
{{< hextra/hero-section >}}
Building Blocks
{{< /hextra/hero-section >}}
</div>

S2DM artifacts are based on these existing resources:

<div class="hx:mb-6">
{{< hextra/hero-section heading="h3" >}}
Modeling Languages
{{< /hextra/hero-section >}}
</div>

- **[GraphQL Schema Definition Language (SDL)](https://graphql.org/learn/schema/)** - Provides a clear, human-readable syntax for defining data structures and relationships, making it easy for SMEs to understand and use without requiring deep technical expertise.
- **[Simple Knowledge Organization System (SKOS)](https://www.w3.org/2004/02/skos/)** - An RDF-based vocabulary that offers a straightforward framework for creating and managing hierarchical classifications and relationships between concepts.

<div class="hx:mb-6">
{{< hextra/hero-section heading="h3" >}}
Tools
{{< /hextra/hero-section >}}
</div>

- **[rdflib](https://rdflib.readthedocs.io)** - To work with RDF data in Python (i.e., SKOS)
- **[graphql-core](https://graphql-core-3.readthedocs.io)** - To work with GraphQL schemas in Python (i.e., SDL)
- **[Others](https://github.com/COVESA/s2dm/blob/main/pyproject.toml)** - Additional supporting tools and dependencies

<div class="hx:mb-8">
{{< hextra/hero-section >}}
Getting Started
{{< /hextra/hero-section >}}
</div>

Ready to start modeling your domain? Here's how:

- 📖 **[Start Modeling](/s2dm/1-modeling-guideline)** - Follow the S2DM data modeling guideline
- 🔧 **[Use Tools](/s2dm/2-tools)** - Manage, evolve, and maintain your domain model with S2DM tools
- 💡 **[See Examples](/s2dm/3-examples)** - Explore real-world examples and use cases
