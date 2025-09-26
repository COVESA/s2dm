---
title:  Simplified Semantic Data Modeling
lead: An approach for modeling data of multiple domains that enables Subject Matter Experts to contribute to controlled vocabularies with minimal data modeling expertise.
---

The _Simplified Semantic Data Modeling_ (`S2DM`) is an approach for modeling data of multiple domains.
It is **_simple_** in the sense that any _Subject Matter Expert_ (SME) could contribute to a controlled vocabulary with minimal data modeling expertise.
Likewise, it is **_semantic_** in the sense that it specifies meaningful data structures, their cross-domain relationships, and arbitrary classification schemes.

{{< callout type="note" >}}
Bear in mind the word _**Simplified**_ in the name.
This approach aims to foster the adoption of (some) good data modeling practices.
It does not intend to re-invent or replace long-standing standards, such as those of the [Semantic Web](https://www.w3.org/2001/sw/wiki/Main_Page).
Therefore, it does not incorporate advanced reasoning capabilities or comprehensive ontologies typically associated with traditional semantic data modeling.
{{< /callout >}}

<div class="w-100 my-4">
  <img src="/images/s2dm_role.png" alt="S2DM Role Overview" class="img-fluid w-100" style="max-width: 100%; height: auto;">
</div>

The figure above ilustrates the role of the `S2DM` approach.
One can distinghish three areas:
the re-use of existing resources (left), the artifacts offered by `S2DM` (center), and the resulting domain data model created and maintained with `S2DM` artifacts (right).

### Getting started
* Get a basic understanding of the [S2DM approach](/docs/approach-overview).
* Model your domain following the [S2DM data modeling guideline](/docs/data-modeling-guideline).
* Maintain your domain model with the support of the provided [S2DM tools](/docs/tools).

{{< callout type="tip" >}}
`S2DM` artifacts are based on the following existing resources. Getting familiar with them is recommended.

- **Modeling languages and vocabularies**
    - [GraphQL Schema Definition Language (SDL)](https://graphql.org/learn/schema/): Provides a clear, human-readable syntax for defining data structures and relationships, making it easy for SMEs to understand and use without requiring deep technical expertise.
    - [Simple Knowledge Organization System (SKOS)](https://www.w3.org/2004/02/skos/): An RDF-based vocabulary that offers a straightforward framework for creating and managing hierarchical classifications and relationships between concepts, facilitating intuitive and semantically rich knowledge organization.

- **Tools**
    - [rdflib](https://rdflib.readthedocs.io): For working with RDF data in Python (e.g., `SKOS`).
    - [graphql-core](https://graphql-core-3.readthedocs.io): For working with `GraphQL` schemas in Python (e.g., `SDL`).
    - [Others](https://github.com/COVESA/s2dm/blob/main/pyproject.toml)
{{< /callout >}}
