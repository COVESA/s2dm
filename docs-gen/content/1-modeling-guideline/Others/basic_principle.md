---
title: Basic principle
weight: 19
chapter: false
---

## Basic principle
The idea is that multiple systems in the physical layer (e.g., databases, streaming platforms, applications, etc.) can share the same concepts.
However, instead of arbitrarily modeling domains in the physical layer, the purpose is to have a unique way for specifying the concepts of common interest and its organizing principles in such a way that they are reused.
This principle is a core part of a [data-centric architecture](https://datacentricmanifesto.org/), reducing undesired duplications and [software waste](https://www.semanticarts.com/software-wasteland/) when it is systematically applied.

```mermaid
graph LR
  subgraph ConceptualLayer
    Person
    Vehicle
    ParkingLot
  end
  subgraph PhysicalLayer
    Database
    StreamingPlatform
    Application
    Other
  end
  ConceptualLayer --> Database
  ConceptualLayer --> StreamingPlatform
  ConceptualLayer --> Application
  ConceptualLayer --> Other
```

In this sense, `S2DM` is an approach to specify those concepts of interest systematically.
A more generic (and elaborated) diagram looks like the following:

```mermaid
graph LR
  subgraph Conceptual layer
    spec_file_1.graphql
    spec_file_2.graphql
    spec_file_N.graphql
    subgraph S2DM Tools
      Composer
      Exporter
      Other
    end
  end
  subgraph Physical layer
    App_SHACL
    App_YAML
    App_JSON
    App_Other
  end
  spec_file_1.graphql --GraphQL schema 1--> Composer
  spec_file_2.graphql --GraphQL schema 2--> Composer
  spec_file_N.graphql --GraphQL schema N--> Composer
  Composer --Merged GraphQL schema--> Exporter
  Composer --Merged GraphQL schema--> Other
  Exporter --VSPEC--> App_YAML
  Exporter --SHACL--> App_SHACL
  Exporter --JSON schema--> App_JSON
  Exporter --Other?--> App_Other
```
