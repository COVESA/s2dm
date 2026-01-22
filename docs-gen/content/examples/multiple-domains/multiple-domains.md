---
title: "Multiple Domains"
description: "Covering cross-references across different domains"
weight: 40
---

This example demonstrates how **S2DM** handles cross-references across different domains. The approach enables modeling complex systems that span multiple domain boundaries while maintaining clear separation of concerns.

```graphql
type Person {
  name: String!
}

type DrivingJourney {
    vehicle: Vehicle!
    occupants: [SeatOccupancy]
}

type SeatOccupancy {
    occupant: Person!
    seat: Seat!
}

extend type Vehicle {
    journeyHistory: [DrivingJourney!]
    chargingHistory: [ChargingSession!]
}

type ChargingSession {
    vehicle: Vehicle!
    paidBy: Person
    chargingStation: chargingStation
}

type chargingStation {
    id: ID!
    # etc...
}
```

## Repository Link

For implementation details and source files, visit the [multiple-domains example](https://github.com/COVESA/s2dm/tree/main/examples/multiple-domains) in the repository.

````
