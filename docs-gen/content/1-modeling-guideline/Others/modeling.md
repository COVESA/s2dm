---
title: Modeling
---

Under refactoring...

## Modeling Guide
> **NOTE:** This document explains how to contribute to an specific model (new or existing).
If you want to contribute to the data modeling approach itself, then see the [Contributing Guide](/guides/contributing/) instead.

> TODO: Work in progress...

## Basic building blocks
We re use following established artifacts:
* For the specification of data structures and possible operations on that data, S2DM re uses the [GraphQL Schema Definition Language (SDL)](https://graphql.org/learn/schema/).
The full feature set is available in the [official GraphQL specification](https://spec.graphql.org).
* For the specification of multiple classification schemes, S2DM uses the [Simple Knowledge Organization System (SKOS)](https://www.w3.org/2004/02/skos/).
To learn more about them, please consult the official documentation.


## Modeling a new domain
* Identify the relevant object types (i.e., entities or classes). Examples: `Vehicle`, `Person`, etc.
* Specify an object `type` of each one (assuming it does not exist yet).
* Add fields to types to represent relationships.
  * If the `field` resolves to a datatype, then assign an `scalar`.
  * If the `field` connects to another object `type`, then assign it.
* Define the set of `enum` values.
* Add other metadata.

## Modeling an existing domain
### Extending an existing model
### Modifying an existing model
#### Extending a type
#### Deprecating elements
It is possible to deprecate fields and enum values with the built-in directive `@deprecated`.
```graphql
type Window {
  position: Int
  openness: Int @deprecated(reason: "Use `position`.")
}
```
To avoid breaking changes, GraphQL does not support the deprecation of types.
To deprecate a complete type, simply deprecate all the fields or values inside.
```graphql
type SomeDeprecatedObjectType {
    fieldOne: string @deprecated(reason: "Use `MyNewType.fieldOne`.")
    ...
    fieldN: string @deprecated(reason: "Use `MyNewType.fieldN`.")
}

type SomeDeprecatedEnum {
    ONE @deprecated(reason: "Use `MyNewEnum`.")
    ...
    TEN @deprecated(reason: "Use `MyNewEnum`.")
}
```
If you want to know more, click [here](https://spec.graphql.org/October2021/#sec--deprecated) to see the specification.

## Model versioning
This simplified modeling approach suggests the use of the `GraphQL` schema language as a mechanism to model concepts as a graph in a simple manner.
It does not mean that one must implement a `GraphQL` server (there might be some advantages to do so, though). It is purely about the language and the community tools that exist.
According to the [official documentation of the language](https://graphql.org/learn/best-practices/#versioning), versioning the schema is considered a bad practice.
> While there’s nothing that prevents a GraphQL service from being versioned just like any other API, GraphQL takes a strong opinion on avoiding versioning by providing the tools for the continuous evolution of a GraphQL schema...

>...GraphQL only returns the data that’s explicitly requested, so new capabilities can be added via new types or new fields on existing types without creating a breaking change. This has led to a common practice of always avoiding breaking changes and serving a versionless API.

However, as the intention is to model a simple conceptual semantic model and not the full API itself, versioning is possible and special care must be given to the rule set.
> TODO: Work in progress...
