---
title:  Simplified Semantic Data Modeling (S2DM)
---

The _Simplified Semantic Data Modeling_ (`S2DM`) is an approach for modeling data of multiple domains.
It is **_simple_** in the sense that any _Subject Matter Expert_ (SME) could contribute to a controlled vocabulary with minimal data modeling expertise.
Likewise, it is **_semantic_** in the sense that it specifies meaningful data structures, their cross-domain relationships, and arbitrary classification schemes.

> [!NOTE]
> Bear in mind the word `Simplified` in the name.
> This approach aims to foster the adoption of (some) good data modeling practices.
> It does not intent to re-invent, nor to replace long-standing standards, such as those of the [Semantic Web](https://www.w3.org/2001/sw/wiki/Main_Page).
> Hence, it does not incorporate advanced reasoning capabilities or comprehensive ontologies typically associated with traditional semantic data modeling.

## `SD2M` role
![Fig:s2dm_role](/s2dm/images/s2dm_role.svg)

### `S2DM` artifacts
`S2DM` consists of two main artifacts:
* [_**`S2DM` data modeling guideline**_](/s2dm/guides/modeling) - It explains how to formalize the data of a domain with the `S2DM` approach. In other words, how to create the specification files that will constitute the core of the conceptual/logical layer.
* [_**`S2DM` tools**_](/s2dm/guides/modeling) - Code that support the proper usage of the `S2DM` data modeling guideline. It helps with the modeling language validation, identifiers, search functions, exporters, etc.

### Building blocks
`S2DM` artifacts are based on these existing resources:

- Modeling languages
  - [GraphQL Schema Definition Language (SDL)](https://graphql.org/learn/schema/) -
  It provides a clear, human-readable syntax for defining data structures and relationships, making it easy for SMEs to understand and use without requiring deep technical expertise.
  - [Simple Knowledge Organization System (SKOS)](https://www.w3.org/2004/02/skos/) -
  `SKOS` is an RDF-based vocabulary that offers a straightforward framework for creating and managing hierarchical classifications and relationships between concepts, facilitating the organization and retrieval of knowledge in a way that is both intuitive and semantically rich.
- Tools
  - [rdflib](https://rdflib.readthedocs.io) - To work with RDF data in Python (i.e., `SKOS`).
  - [graphql-core](https://graphql-core-3.readthedocs.io) - To work with `GraphQL` schemas in Python (i.e., `SDL`).
  - [Others](https://github.com/COVESA/s2dm/blob/main/pyproject.toml)

## Getting started
* You can start modeling your domain by following the [_**`S2DM` data modeling guideline**_](/s2dm/1-modeling-guideline).
* You can manage, evolve, and maintain your domain model by using the [_**`S2DM` tools**_](/s2dm/2-tools).
