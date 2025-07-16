---
title: Pre-defined elements
weight: 1
chapter: false
---

![fig:s2dm_pre_defined_elements](/s2dm/images/s2dm_pre_def_elements.svg)

### Units
Units are represented as enum values. For example:
```graphql
enum VelocityUnitEnum {
  KILOMETER_PER_HOUR
  METERS_PER_SECOND
}
```
The name of the enum itself refers to the quantity kind (e.g., `Velocity`).
A set of commonly used units is provided in the file [`unit_enums.graphql`](https://github.com/COVESA/s2dm/blob/main/src/s2dm/spec/unit_enums.graphql).

> [!NOTE]
> [It is planned](https://github.com/COVESA/s2dm/issues/43) to adopt and reuse an existing standard data model for units.
> At the moment, the units file is inspired by [COVESA VSS Units file](https://github.com/COVESA/vehicle_signal_specification/blob/main/spec/units.md).
> The tentative model that will be used in the future is the [QUDT units](http://www.qudt.org/doc/DOC_VOCAB-UNITS-ALL.html).


### Custom scalars
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

### Common types

#### Common enumeration sets
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

#### Common objects of interest
Under construction...
