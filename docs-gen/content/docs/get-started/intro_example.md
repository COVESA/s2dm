---
title: Example -- Coffee shop domain
description: A step-by-step guide to creating your first data model with S2DM using a coffee shop example.
weight: 1
toc: true
---

{{< img src="s2dm/images/coffee_shop.png" alt="Example banner of a coffee shop" >}}

This example provides a general non-technical overview of the S2DM approach.
Imagine that we want to describe the data of a coffee shop business.
In this domain, we might identify aspects such as:
- Menu items (e.g., beverages)
- Customer orders
- Tables (e.g., occupied or available)
- Appliances (e.g., coffee machines)
- And more.

We proceed as follows:

{{< img src="s2dm/images/coffee_shop_example_flow.png" alt="Example banner of a coffee shop" >}}

A domain expert familiar with the "coffee shop" (i.e., a subject matter expert) models the domain using a friendly, machine-readable syntax. 
The resulting model can be validated, explored, or combined using supporting tools. 
Finally, the model can be exported into specific formats for use in one or more downstream systems. 
For example, such a system could be a database or a web application for the coffee shop.
These steps are elaborated in more detail below.

---
# Modeling
A domain data model is an abstraction that characterizes the most relevant aspects of a subject matter.
Steps 1 to 4 demonstrate how simple it is to formalize the basics of a domain.

## Step 1: Identify Relevant Types

Think of the most relevant **entities** that exist in the coffee shop.
These might include tangible things (like a `Table` or `Appliance`), data records (like an `Order` or `Customer`), or events (like an `OrderPlaced`).
An entity in S2DM is called a `type`.
In general, anything that can have properties you are interested in could be a type in the model.

Let us focus on the following types:
- `Beverage` - Different kinds of coffee beverages you offer
- `Order` - The record of an order served in the coffee shop
- `Table` - Places in the shop where customers can sit
- `Customer` - People who place orders


## Step 2: Specify Fields That Characterize Each Type

What makes a particular type unique? 
Think of properties, attributes, or characteristics that are important in the domain.
Especially those whose data would be relevant to store, exchange, or read.
In S2DM, such a property, attribute, or characteristic of a type is known as a `field`.

For instance:
- `Beverage` 
    - `name` - Beverage name
    - `price` - Cost in currency units
- `Order`
    - `table` - Where it is served
    - `customer` - Who placed the order
- `Table`
    - `state` - Whether it is occupied or not
- `Customer`
    - `name` - Customer name



## Step 3: Assign Fields a Particular Output
Think of the concrete data associated with each field.
The following questions can help:

**Do we expect a single value for this field?**
In other words, does the data for this field resolve to a unique value like text or a number?
If so, the field likely resolves to a primitive data type like `Int`, `Float`, `String`, `Boolean`, and so on.
In S2DM, such an output is called a `scalar`.

Examples might include:
| Field            | Output   |
|------------------|----------|
| `Beverage.name`  | `String` |
| `Beverage.price` | `Float`  |
| `...`            | `...`    |



**Is this field related to another element I already have?**
If so, the field resolves to another type. 
Sometimes it is useful to draw elements in a graph with nodes and relationships.
This helps clarify dependencies.
In this sense, the node in the graph represents a `type`, whereas an edge represents the connection between types.

{{< img src="s2dm/images/eg_v1_graph_model.png" alt="Example graph model with nodes and relationships" >}}

To identify the meaning of an edge (i.e., an arrow that connects two types), assign the verb that best matches what you want to describe.
Often, there are a couple of possibilities depending on the perspective.
For instance:
* Relationship between `Order` and `Table`:
  - An `Order` is served at a particular `Table`
  - A `Table` serves certain `Order`
* Relationship between `Order` and `Customer`:
  - An `Order` is placed by a `Customer`
  - A `Customer` places an `Order`

Either direction expresses the same relationship.
This duality in the graph model is commonly known as an inverse property.
What is important here is that it is sufficient to select one.
So, pick the one that makes the most sense in the domain.
For example, when we talk about an `Order`, we want to have direct access to the information about the `Table` and the `Customer`.
Hence, our example selects:
* `Order -"served at"-> Table` 
* `Order -"placed by"-> Customer`. 

| Field            | Output   |
|------------------|----------|
| `Order.customer` | `Customer` |
| `Order.table`    | `Table`    |
| `...`            | `...`      |


## Step 4: Write It in Machine-Readable Language
With the previous steps, we gathered all the necessary information to represent the basics of our domain.
Now, it is time to translate that into an appropriate machine-readable language.
S2DM adopts the [Schema Definition Language (SDL)](https://graphql.org/learn/schema/#type-language) from the [GraphQL](https://graphql.org) ecosystem as its modeling language. 

{{< callout note >}} More aspects about SDL and other technical details are covered in subsequent sections of the documentation. {{< /callout >}}

### Formalizing a Type
Let us consider our `Beverage` type from the example. Using the appropriate syntax, it will look like this:

```graphql
type Beverage {
    # <-- It is empty for now
}
```

Our type `Beverage` acts as a container structure that can have one or multiple fields within the enclosing curly brackets `{...}`.


### Formalizing Fields
Within the container type, one can specify fields as `key: value` pairs, where `key` is the name of the field, and `value` is the output associated with it.

There are fields like `Beverage.name` and `Beverage.price` which resolve to the scalars `String` and `Float` respectively:

```graphql
type Beverage {
    name: String
    price: Float
}
```

While other fields connect to other types such as `Order.table` and `Order.customer`:

```graphql
type Order {
    table: Table
    customer: Customer
}
```

### Repeat as Needed
Continue to specify types, fields, and their outputs until the most relevant aspects are reflected.
A first draft of this example model might look as follows:

```graphql
type Beverage {
  name: String
  price: Float
}

type Order {
  table: Table
  customer: Customer
}

type Table {
  isOccupied: Boolean
}

type Customer {
  name: String
}
```

That is pretty much the essence of data modeling in S2DM.
It is intentionally simple to empower domain experts.

---
# Using the Tools
Once you have the model, you can use the supporting tools to maintain and evolve it.
The tools help you, among other things, to validate and export it to other formats.
{{< callout note >}} Tools are offered as a Command Line Interface (CLI). More on that is explained in the dedicated section of the documentation. {{< /callout >}}

## Step 5: Use the Supporting Tools

### Validating the Model
We first make sure that our model is compliant with the expected syntax of the language.
This can be done with one command as follows:
```bash
s2dm validate --schema <path to the model file or directory> --output <my_valid_schema.graphql>
```

This command will create a valid composed schema file from the given source, indicating that it is compliant.
The tool logs information about the process like the following:
```bash
(s2dm) ... % s2dm validate graphql -s examples/coffee-shop/v1/schema.graphql -o examples/coffee-shop/v1/validated.graphql
    INFO     Successfully built the given GraphQL schema string.                                        
    INFO     The provided schema has no Query type.                                                     
    INFO     A generic Query type to the schema was added.                                              
    INFO     Running command: ...                                                
    INFO     Process completed with return code: 0                                                                               
 Saved to .../examples/coffee-shop/v1/validated.graphql
```

In contrast, the validation of a model that uses the wrong syntax will not succeed.
For example:
```graphql
type Beverage ( 
  name: string # <-- Unknown scalar "string"
  price: float # <-- Unknown scalar "float"
) # <-- Wrong enclosing symbols "(...)"
```
This time, we used the wrong enclosing symbols `(...)` instead of `{...}` and unkown outputs like `string` instead of `String`.
So, the validation fails as soon as one mistake is found:
```bash
...
Syntax Error: Unexpected '('.

GraphQL request:1:15
1 | type Beverage ( 
  |               ^
2 |   name: string 
```

### Exporting the Model to Other Formats
A valid model can also be exported for downstream use.
Let us assume that the database requires a JSON schema.
Similar to the validation, the tools let you export with a command like:

```bash
s2dm export jsonschema --schema examples/coffee-shop/v1/schema.graphql --output examples/coffee-shop/v1/output.json
```

The result would look as follows:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "Beverage": {
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string"
        },
        "price": {
          "type": "number"
        }
      },
      "type": "object"
    },
    "Order": {
      "additionalProperties": false,
      "properties": {
        "table": {
          "$ref": "#/$defs/Table"
        },
        "customer": {
          "$ref": "#/$defs/Customer"
        }
      },
      "type": "object"
    },
    "Table": {
      "additionalProperties": false,
      "properties": {
        "isOccupied": {
          "type": "boolean"
        }
      },
      "type": "object"
    },
    "Customer": {
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "Query": {
      "additionalProperties": false,
      "properties": {
        "ping": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "type": "object",
  "title": "GraphQL Schema",
  "description": "JSON Schema generated from GraphQL schema"
}
```

Congratulations! You have followed along with the entry-level example of the S2DM approach.

---

# Closing Remarks
The real value of S2DM is unlocked when domains are modeled systematically and in a compatible manner. 
The supporting tools are most effective when integrated into continuous integration workflows, automating processes during the maintenance and evolution of models. 
Further details and best practices are covered throughout the rest of the documentation.










