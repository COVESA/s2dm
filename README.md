<h2 align="center">
 Simplified Semantic Data Modeling (S2DM)
</h2>

`S2DM` is an approach for modeling data of multiple domains.
It is **_simple_** in the sense that any Subject Matter Expert (SME) could contribute to a controlled vocabulary with minimal data modeling expertise.
Likewise, it is **_semantic_** in the sense that it specifies meaningful data structures, their cross-domain relationships, and arbitrary classification schemes.

> [!TIP]
> Bear in mind the word `Simplified` in the name.
> This approach aims to foster the adoption of (some) good data modeling practices.
> It does not intent to re-invent, nor to replace long-standing standards, such as those of the [Semantic Web](https://www.w3.org/2001/sw/wiki/Main_Page).
> Hence, this approach does not incorporate advanced reasoning capabilities or the use of comprehensive ontologies typically associated with traditional semantic data modeling.

`S2DM` adopts data modeling best practices and reuses the following elements:

- [GraphQL Schema Definition Language (SDL)](https://graphql.org/learn/schema/).
  It provides a clear, human-readable syntax for defining data structures and relationships, making it easy for SMEs to understand and use without requiring deep technical expertise.
- [Simple Knowledge Organization System (SKOS)](https://www.w3.org/2004/02/skos/).
  It offers a straightforward framework for creating and managing hierarchical classifications and relationships between concepts, facilitating the organization and retrieval of knowledge in a way that is both intuitive and semantically rich.

To learn more about the background that has led to S2DM, as well as its design principles, please read the [S2DM Approach Primer](docs/APPROACH_PRIMER.md).
For instructions on how to model the data of a particular domain following the `S2DM` approach, please read the [Data modeling guideline](docs/MODELING_GUIDE.md)

## Contributing

See [here](docs/CONTRIBUTING.md) if you would like to contribute.
