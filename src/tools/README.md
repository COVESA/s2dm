# Tools

```mermaid
graph LR
  subgraph Conceptual layer - S2DM
    source_file_1
    source_file_2
    source_file_N
    subgraph tools
      Composer
      Exporter
    end
  end
  subgraph Physical layer
    App_SHACL
    App_YAML
    App_JSON
  end
  source_file_1 --GraphQL schema 1--> Composer
  source_file_2 --GraphQL schema 2--> Composer
  source_file_N --GraphQL schema N--> Composer
  Composer --Merged GraphQL schema--> Exporter
  Exporter --SHACL--> App_SHACL
  Exporter --YAML--> App_YAML
  Exporter --JSON schema--> App_JSON
```

## Composer

### Modularization
The tool can load multiple GraphQL schema files at once, as long as they are located in the same directory. This is currently done in the `utils` module with the [load function of the `Ariadne` package](https://ariadnegraphql.org/docs/modularization), which validates the syntax of every loaded file.
Therefore, it is possible to split a domain model into multiple smaller files. Such modularity is recommended to facilitate the further extension and maintenance of the domain model.
For example, in the figure shown above, schemas `1`, `2`, ..., `N` are merged into one before calling the exporter.

### Model validator
> TODO: Mechanisms to assess the integrity of the model. Examples: unique names, proper use of directives, completeness of types used within the model, correct construction of unique identifiers, etc.

### Arbitrary selection of concepts
> TODO: Mecahanism to arbitrarily select a sub set of the specification with only the desired concepts. Example: via the use of GraphQL introspection.

## Exporters
### General information about exporters
A model done with the GraphQL SDL represents an specification.
The actual implementation of it is out of the scope.
However, to facilitate the implementation, the exporter tool parses the specified model and creates the artifact that is needed by the system in the physical layer.

#### Available exporters
The tools can currently export a given model into:
* SHACL - `tools/to_shacl.py`

#### Supported field cases by exporter
> See `docs/MODELING_GUIDE.md` for more information on cases for fields and the custom directives, such as @noDuplicates.

| Case | `outputType`| SHACL|
|----------|----------|----------|
| **Nullable Singular Field**   | `NamedType`   | ✅ |
| **Non-Nullable Singular Field**   | `NamedType!`   | ✅ |
| **Nullable List Field**   | `[NamedType]`   | ❌ |
| **Non-Nullable List Field**   | `[NamedType]!`   | ❌ |
| **Nullable List of Non-Nullable Elements**   | `[NamedType!]`   | ❌ |
| **Non-Nullable List of Non-Nullable Elements**   | `[NamedType!]!`   | ❌ |
| **Nullable Set Field**   | `[NamedType] @noDuplicates` | ✅ |
| **Non-Nullable Set Field**   | `[NamedType]! @noDuplicates`   | ✅|


### SHACL exporter
This exporter translates the given GraphQL schema to [SHACL](https://www.w3.org/TR/shacl/).

The [Shapes Constraint Language (SHACL)](https://www.w3.org/TR/shacl/) is a framework used to validate data in [Resource Description Framework (RDF)](https://www.w3.org/RDF/) format.
In other words, if you work with the RDF graph data model and triple stores (i.e., RDF-based graph databases), SHACL is used to validate a certain RDF data graph.
Think of it as a set of rules or criteria that your data needs to meet. If you're working with data that follows certain structures or patterns, SHACL helps make sure everything is in the right place and follows the right format. It's like having a checklist to ensure your data is accurate and consistent, making it easier to work with and understand. This is especially useful in fields like data management and semantic web technologies, where data integrity is crucial.

#### RDF in a nutshell
The core of RDF is a triple consisting of:
```mermaid
graph LR
  subject -- predicate --> object
```
So, an RDF data graph consists of a set of such triples. For example:
```mermaid
graph LR
  Max --a--> Person
```
```mermaid
graph LR
  Vehicle --hasOccupant--> Person
```
```mermaid
graph LR
  Max --a--> Person
```

Since every resource is uniquely identified in RDF, the set of triples resembles a graph.
Abstract concepts define the most generic `Terminology` (aka., `TBox`).
For example, `Person` and `Vehicle`.
More specific concepts constitute the `Categories` (aka., `CBox`) of a domain.
For example, `CarOccupant` and `Car`.
Finally, the actual data (aka., `ABox`) is connected to the upper concepts that provide context.
For example, `Max` and `BMW_X1`.

```mermaid
graph RL
  subgraph TBox
    Vehicle
    Person
  end
  subgraph CBox
    Car
    CarOccupant
  end
  subgraph ABox
    BMW_X1
    Max
  end

  Vehicle --hasOccupant--> Person
  CarOccupant --subClassOf--> Person
  Car --subClassOf--> Vehicle
  Max --a--> CarOccupant
  BMW_X1 --a--> Car
  BMW_X1 --hasOccupant--> Max
```

SHACL is the language that specifies constraints that allow the validation of an RDF data graph.
More specifically:
* The `subject` can be constrained by a `nodeShape`.
* The `predicate` can be constrained by a `propertyShape`

#### Rules for SHACL property shapes
For any field that resolves in scalar:
- nodeKind is sh:Literal
- name is the field name from the GraphQL schema
- path is the field name from the GraphQL schema
- datatype is the xsd literal corresponding to the scalar type

For any field that resolves in a named type:
- nodeKind is sh:IRI
- name is the named type name from the GraphQL schema
- path is the generic "model:has"
- class is the named type name from the GraphQL schema
- node is the named type shape


#### Note on supported field cases
Implicitly, lists in the default field cases GraphQL refer to an array of values that could be duplicated.
In order to explicitly say that the intended content of the array should function as a set of unique values instead, the custom directive @noDuplicates is introduced.
```gql
type Person {
    nicknamesList: [String]  # Array with possible duplicate values
    nicknamesSet: [String] @noDuplicates  # Set of unique values
}
```

The SHACL exporter does not support lists at the moment bacause adding the cardinality constraints to the list elements represent the addition of an extra blank node, and the existing use cases do not currently need that.

##### Example of a supported structure
```gql
type Cabin {
  doors: [Door] @noDuplicates
  ...
}

type Door {
  instanceTag: Area2x2
}

type Area2x2 @instanceTag {
  row: TwoRows
  column: TwoColumns
}

enum TwoRows {
  FRONT
  REAR
}

enum TwoColumns {
  DRIVERSIDE
  PASSENGERSIDE
}
```
```mermaid
graph LR
  Cabin -- has --> Door.ROW1.DRIVERSIDE
  Cabin -- has --> Door.ROW1.PASSENGERSIDE
  Cabin -- has --> Door.ROW2.DRIVERSIDE
  Cabin -- has --> Door.ROW2.PASSENGERSIDE
```
Here, each of the `object` nodes is an instance of a `Door` with a particular instance tag given as `sh:name` (e.g., `Door.ROW1.DRIVERSIDE`).
Therefore, the GraphQL non-nullable type modifier `!` can be applied only to the elements of the array and not to the array itself.
That is why not all field cases are supported at the momment by the SHACL exporter.

##### Example of an unsupported structure
```gql
type Cabin {
  doors: [Door]
  ...
}
```
```mermaid
graph LR
  Cabin -- doors --> BlankNode
  BlankNode -- has --> Door.ROW1.DRIVERSIDE
  BlankNode -- has --> Door.ROW1.PASSENGERSIDE
  BlankNode -- has --> Door.ROW2.DRIVERSIDE
  BlankNode -- has --> Door.ROW2.PASSENGERSIDE
```
This graph structure is not currently supported.
Here, there are two cardinalities: one for the list, and another for the elements in the list.

Please, refer to the CLI help for usage reference.
```bash
s2dm shacl --help
```

### JSON schema exporter

## Composer
Instead of modeling a huge monolithic model, GraphQL schemas can be specified in multiple small ones (aka., sub graphs).
Then, specific elements from different sub models can be stiched together to form the composed model with the structure needed.
To learn more about it, please refer to the [official documentation of the GraphQL Schema Definition Language](https://graphql.org/learn/federation/).
> TODO: This is part of the feature roadmap.
