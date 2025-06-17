# Modeling Guide
> **NOTE:** This document explains how to contribute to an specific model (new or existing).
If you want to contribute to the data modeling approach itself, then see the [Contributing Guide](docs/CONTRIBUTING.md) instead.

> TODO: Work in progress...

## Basic building blocks
We re use following established artifacts:
* For the specification of data structures and possible operations on that data, S2DM re uses the [GraphQL Schema Definition Language (SDL)](https://graphql.org/learn/schema/).
The full feature set is available in the [official GraphQL specification](https://spec.graphql.org).
* For the specification of multiple classification schemes, S2DM uses the [Simple Knowledge Organization System (SKOS)](https://www.w3.org/2004/02/skos/).
To learn more about them, please consult the official documentation.

## Predefined elements
### Units
A set of commonly used units is provided in the file `/spec/unit_enums.graphql`. For example:
```graphql
enum Velocity_Unit_Enum {
  KILOMETER_PER_HOUR
  METERS_PER_SECOND
}
```
> TODO: Unify the units reference from the given sources.
* [COVESA VSS Units file](https://github.com/COVESA/vehicle_signal_specification/blob/main/spec/units.md).
* [QUDT units](http://www.qudt.org/doc/DOC_VOCAB-UNITS-ALL.html)
### Scalars
Scalars in GraphQL are basically the datatypes to which a `field` resolves.
GraphQL supports a few built-in scalars such as `Int`, `Float`, `String`, `Boolean`, and `ID`.
It is possible to define custom ones.
The file `/spec/custom_scalars.graphql` contains custom scalars that could be referenced in the model.

### Custom directives


#### @instanceTag
```gql
directive @instanceTag on OBJECT
```
> TODO: Add description and example
#### @cardinality
```gql
directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION
```
> TODO: Add description and example
#### @range
```gql
directive @range(min: Float, max: Float) on FIELD_DEFINITION
```
> TODO: Add description and example
#### @noDuplicates
```gql
directive @noDuplicates on FIELD_DEFINITION
```
Considering the following generic object:
```gql
type MyObject {
    field: <outputType>
}
```
By default, the GraphQL SDL let us express the following six combinations for output types in fields:


| Case | Description | `outputType`|
|----------|----------|----------|
| **Nullable Singular Field**   | A singular element that can also be null.   | `NamedType`   |
| **Non-Nullable Singular Field**   | A singular element that cannot be null.   | `NamedType!`   |
| **Nullable List Field**   | An array of elements. The array itself can be null.   | `[NamedType]`   |
| **Non-Nullable List Field**   | An array of elements. The array itself cannot be null.   | `[NamedType]!`   |
| **Nullable List of Non-Nullable Elements**   | An array of elements. The array itself can be null but the elements cannot.   | `[NamedType!]`   |
| **Non-Nullable List of Non-Nullable Elements**   | List and elements in the list cannot be null.   | `[NamedType!]!`   |

Implicitly, lists here refer to an array of values that could be duplicated.
In order to explicitly say that the intended content of the array should function as a set of unique values instead, the custom directive @noDuplicates is introduced.
```gql
type Person {
    nicknamesList: [String]  # Array with possible duplicate values
    nicknamesSet: [String] @noDuplicates  # Set of unique values
}
```

### Common enumeration sets
In some cases, it is practical to refer to a particular set of values that might fit to multiple use cases.
For example, the zone inside the cabin of a car could be re used by the `Door` and the `Window`
It could be modeled as:
```graphql
type InCabinZone {
    row: InCabinRowEnum!
    side: InCabinSide!
}

enum InCabinRowEnum {
    FRONT
    REAR
}

enum InCabinSide {
    DRIVER_SIDE
    PASSENGER_SIDE
}
```

Then, it can be referenced from:
```graphql
Window {
    instance: InCabinZone
    ...
}

Door {
    instance: InCabinZone
    ...
}
```
Such common enumeration sets are available in the file `/spec/common_enums.graphql`.

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
