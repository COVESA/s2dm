---
title:  Simplified Semantic Data Modeling
---

The _Simplified Semantic Data Modeling_ (`S2DM`) is an approach for modeling data of multiple domains.
It is **_simple_** in the sense that any _Subject Matter Expert_ (SME) could contribute to a controlled vocabulary with minimal data modeling expertise.
Likewise, it is **_semantic_** in the sense that it specifies meaningful data structures, their cross-domain relationships, and arbitrary classification schemes.

> [!NOTE]
> Bear in mind the word _**Simplified**_ in the name.
> This approach aims to foster the adoption of (some) good data modeling practices.
> It does not intent to re-invent, nor to replace long-standing standards, such as those of the [Semantic Web](https://www.w3.org/2001/sw/wiki/Main_Page).
> Hence, it does not incorporate advanced reasoning capabilities or comprehensive ontologies typically associated with traditional semantic data modeling.

![Fig:s2dm_role](/s2dm/images/s2dm_role.svg)
The figure above ilustrates the role of the `S2DM` approach.
One can distinghish three areas:
the re-use of existing resources (left), the artifacts offered by `S2DM` (center), and the resulting domain data model created and maintained with `S2DM` artifacts (right).

### Getting started
* Get a basic understanding of the [S2DM approach](/s2dm/1-approach-overview).
* Model your domain following the [S2DM data modeling guideline](/s2dm/2-data-modeling-guideline).
* Maintain your domain model with the support of the provided [S2DM tools](/s2dm/3-tools).

> [!TIP]
> `S2DM` artifacts are based on the following existing resources. Getting familiar with them is recomended.
>
> - Modeling languages and vocabularies
>   - [GraphQL Schema Definition Language (SDL)](https://graphql.org/learn/schema/) -
> It provides a clear, human-readable syntax for defining data structures and relationships, making it easy for SMEs to understand and use without requiring deep technical expertise.
>   - [Simple Knowledge Organization System (SKOS)](https://www.w3.org/2004/02/skos/) -
> `SKOS` is an RDF-basedd vocabulary that offers a straightforward framework for creating and managing hierarchical classifications and relationships between concepts, facilitating the organization and retrieval of knowledge in a way that is both intuitive and semantically rich.
> - Tools
>   - [rdflib](https://rdflib.readthedocs.io) - To work with RDF data in Python (i.e., `SKOS`).
>   - [graphql-core](https://graphql-core-3.readthedocs.io) - To work with `GraphQL` schemas in Python (i.e., `SDL`).
>   - [Others](https://github.com/COVESA/s2dm/blob/main/pyproject.toml)
