---
title: Extended Example -- Coffee shop domain
description: Extended example of the already introduced coffee shop domain model.
weight: 10
toc: true
---


- `CoffeeShop` - Establishment that sells coffee beverages
- `Appliance` - Equipment like coffee machines, blenders (multiple instances!)




- `Order`
    - `beverages` - What was ordered


- `CoffeeShop`
    - `shopId` - Unique identifier
    - `menu` - Items that are offered
    - `orders` - The orders placed in this shop
    - `appliances` - Items that are part of this shop
    - `tables` - Places available for the customers
- `Appliance`
    - `kind` - Kind of appliance (Coffee Machine, Espresso Machine, etc.)
    - `isWorking` - Current operational status



| Field                  | Output      | Cardinality |
|------------------------|-------------|-----------|
| `CoffeeShop.menu`      | `Beverage`  | 1:N         |
| `CoffeeShop.orders`    | `Order`     | 1:N         |
| `CoffeeShop.tables`    | `Table`     | 1:N         |
| `CoffeeShop.appliances`| `Appliance` | 1:N         |




```graphql
type CoffeeShop {
  menu: [Beverage]
  orders: [Order]
  appliances: [Appliance]
  tables: [Table]
}

type Appliance {
  kind: String
  isWorking: Boolean
}

extend type Order {
  beverages: [Beverage]
}
```

Note that some outputs are enclosed with brackets `[...]`, such as in `menu: [Beverage]`.
This is known as a [list type modier](https://graphql.org/learn/schema/#list), and means that the `menu` field is expected to be composed of multiple elements of the type `Beverage`.
In other words, that _"a menu has multiple beverages."_
This and other constructs of the GraphQL SDL language are exemplified later in the documentation.