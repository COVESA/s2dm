---
title: "GraphQL Voyager"
description: "Interactive GraphQL Voyager visualization of the seat domain model"
layout: fullwidth
toc: false
weight: 20
---

Explore the seat capabilities domain model through an interactive [GraphQL Voyager](https://github.com/graphql-kit/graphql-voyager) visualization. This comprehensive schema, derived from the [Vehicle Signal Specification (VSS)](https://covesa.github.io/vehicle_signal_specification/) `Seat` branch, demonstrates how **S2DM** effectively models complex automotive domain relationships including nested components (backrest, headrest, seating), enumerated values, and rich type relationships.

{{< callout type="tip" >}}
**Usage:** Click and drag to navigate • Click types for details • Use the sidebar to search and explore documentation • Zoom with mouse wheel for different perspectives.
{{< /callout >}}

---

{{< graphql-voyager-builtin schema="/examples/seat-to-vspec/full_sdl.graphql" height="1000px" title="Seat Capabilities Domain Model" hideDocs="false" hideSettings="false" hideVoyagerLogo="true" showLeafFields="true" skipRelay="true" skipDeprecated="true" >}}
