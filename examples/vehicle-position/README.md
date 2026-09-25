# Vehicle position: a fifth classification scheme

A worked example applying the S2DM multiple-classification-schemes pattern to a
live, unresolved question in COVESA VSS: how to attach stable, machine-readable
meaning to vehicle position identifiers.

> [!NOTE]
> This is an example demonstrating the pattern, not an adopted COVESA
> specification. The namespace `http://example.org/vss-position#` follows the
> convention of [`../multiple-classification-schemes/skos.ttl`](../multiple-classification-schemes/skos.ttl);
> a real deployment would use a COVESA-allocated namespace.

## Why position is a good fit for this pattern

[`../multiple-classification-schemes/skos.ttl`](../multiple-classification-schemes/skos.ttl)
shows the same VSS concepts (`Seat`, `Mirror`, `Window`, `Trunk`) classified
simultaneously under four independent schemes — physical membership, movement
type, material, occupant interface. Position is a natural fifth facet: it
cross-classifies by *where* a part is, which none of the existing four express,
and it is orthogonal to all of them.

It is also a facet with an unusual property that makes it a useful test of the
pattern: **not all of its concepts are frame-fixed.** `Left` is a direction in a
standardised axis system. `DriverSide` is not — it is a function of vehicle
configuration that *yields* left or right. Modelling both in one scheme without
collapsing the distinction is the interesting part, and it is where the first
draft of this file was wrong (see [SKOS integrity](#skos-integrity) below).

## The underlying VSS question

VSS instance identifiers today mix several conventions, and four open items in
the VSS tracker are the same underlying problem:

| Item | Problem |
|---|---|
| [PR #940](https://github.com/COVESA/vehicle_signal_specification/pull/940) | **BREAKING: Wheel designation refactoring.** Replaces `["Left","Right"]` wheel instances with numeric codes, citing ISO 11992-2 and SAE J1939-71: axles `Row1,2,3…` from the front, wheels outward from the centreline — `Pos8` centre, `Pos7…Pos1` left, `Pos9…Pos15` right. Standard catalog default becomes `["Pos7","Pos9"]`; motorbike profile `["Pos8"]`. |
| [Issue #879](https://github.com/COVESA/vehicle_signal_specification/issues/879) | `Cabin.HVAC.Station` uses `["Driver","Passenger"]` while `Occupant`, `Body.Mirrors`, `Cabin.Door`, `Cabin.Seat` and `InteriorLights` all use `["DriverSide","Middle","PassengerSide"]`. |
| [Issue #642](https://github.com/COVESA/vehicle_signal_specification/issues/642) | Proposes replacing enumerated instances with row/position attributes, and notes explicitly: *"We could even support to both have a Left/Right-approach as well as Driver/Passenger-approach and let the server manage the mapping."* |
| [PR #919](https://github.com/COVESA/vehicle_signal_specification/pull/919) | Decouples instance handling from the model, floating `instance_type: ROW_POS` as syntax. A published concept scheme is the natural referent for such a type. |

PR #940 keeps `Left`/`Right` on the new `Chassis/HalfAxle` branches, so the
numeric codes and the descriptive terms are not in competition. What is missing
is a place to say what either of them *means*, which is what a SKOS scheme
supplies — and which the mapping in #642 would need in order to be written down.

There is a third problem visible only once the tokens are inventoried: **VSS
v6.1 has three spellings of "laterally central"** — `Middle` (Seat, Door,
Occupant, Mirrors, InteriorLights), `Center` (ADAS) and `Central`
(`Vehicle.ControlUnit`) — plus `FrontMiddle`/`RearMiddle` inside compounds.

## What the scheme contains

20 concepts, grouped into three `skos:Collection`s:

- **`GeometricPositions`** — frame-fixed: `Left`, `Right`, `LateralCenter`,
  `Front`, `Rear`, `Upper`, `Lower`, `Outboard`, `Inboard`, and the six
  compounds VSS uses as single tokens (`FrontLeft`, `FrontCenter`,
  `FrontRight`, `RearLeft`, `RearCenter`, `RearRight`).
- **`ConfigurationDependentPositions`** — `DriverSide`, `PassengerSide`.
- **`OrdinalPositions`** — `RowOrdinal`, `WheelPositionCode`. Used with an
  integer rather than enumerated, so the vocabulary carries no arbitrary upper
  bound and no fifteen near-identical concepts whose only content is a number.

Plus `PositionUnspecified` for the `AnyPosition` wildcard, so that token → concept
is a total function.

### Three modelling choices worth reviewing

**1. `vssInstanceToken` annotations do the normalisation.** Each concept records
the literal VSS token(s) that denote it, so tooling can go token → concept →
label without string parsing:

```turtle
vsspos:LateralCenter a skos:Concept ;
    skos:prefLabel "Lateral centre"@en ;
    skos:altLabel "Middle"@en , "Center"@en , "Central"@en ;
    vsspos:vssInstanceToken "Middle" , "Center" , "Central" , "Pos8" .
```

This closes issue #879 and the Middle/Center/Central split **without a breaking
rename** — the tokens stay as they are and are declared synonymous. It needs no
numeric codes and does not depend on PR #940 landing, which makes it the
lowest-risk increment of the whole idea.

It is also why compounds are modelled explicitly rather than derived: string
splitting looks like it would work until `RearLeft1` and `RearLeft2`, where the
trailing digit is a control-unit index, not a position.

**2. Configuration-dependent concepts are resolved, not subtyped.**

```turtle
vsspos:DriverSide a skos:Concept ;
    skos:related vsspos:Left , vsspos:Right ;
    vsspos:resolvesVia schema:steeringPosition ;
    skos:note "schema:LeftHandDriving implies vsspos:Left; schema:RightHandDriving implies vsspos:Right." .
```

`schema:steeringPosition`, with `schema:LeftHandDriving` /
`schema:RightHandDriving`, is an existing widely-deployed term for exactly this
flag, so nothing new is minted for it.

**3. QUDT is an optional annotation on six concepts, not the backbone.** VSS
already depends on QUDT (186 `qudt:` references in `spec/units.yaml`), and this
repo now carries `examples/units/external_qudt`, so the precedent is real. But
QUDT reaches only the three axis-polarity pairs — 6 of roughly 20
position-bearing VSS tokens — and it defines **no** property for attaching an
`AxialOrientationType` to a part: the only three properties with that range
(`qudt:pitch/roll/yawRotationDefinition`) are about rotation axes. Hence a
scheme-local annotation property:

```turtle
vsspos:Left vsspos:axialOrientation coords:PositiveY .
```

Note also that `qudt:VehicleCoordinateSystem` is **not** usable here despite its
name: its own `dcterms:description` reads verbatim *"A sub-type of 'Aerospace
coordinate system'."*, it subclasses `qudt:AerospaceCoordinateSystem`, and its
siblings are `TrajectoryCoordinateSystem`, `LunarCoordinateSystem`,
`MarsCoordinateSystem` and `ThreeBodyRotatingCoordinateSystem`. "Vehicle" there
means launch vehicle.

## Reference frame

Geometric concepts are grounded in **ISO 8855:2011 only** (Xv forward, Yv
**left**, Zv up). This matters: SAE J670e inverts the lateral sign (+Y right),
so `Left → coords:PositiveY` is *wrong* in a J670e frame. J670:2008 permits both
orientations but is scoped to two-axle passenger cars, while ISO 8855 covers
multi-axle commercial vehicles — which is the case driving PR #940. Citing both
standards, as is often done informally, makes the mapping ambiguous.

Seating terms (`Outboard`, `Inboard`) come from **49 CFR 571 (FMVSS)**, which
defines "outboard designated seating position"; ISO 8855 is a vehicle-dynamics
vocabulary and does not cover seating.

## SKOS integrity

The first draft of this scheme asserted both
`vsspos:Left skos:related vsspos:DriverSide` and
`vsspos:DriverSide skos:broadMatch vsspos:Left`. That is inconsistent:
`skos:broadMatch` is a sub-property of `skos:broader` and hence of
`skos:broaderTransitive`, which **SKOS integrity condition S27** declares
disjoint with `skos:related`. It was wrong on a second count too —
`skos:broadMatch` is a `skos:mappingRelation`, for links *between* schemes, and
both concepts were in this one.

This is worth flagging because it is a mistake the pattern invites: when one
facet's concepts relate to another's, `*Match` properties look like the obvious
tool and are not. The current file uses `skos:related` only, which is also the
semantically correct answer — "driver's side" is not a *kind of* "left".

Validated with `rdflib`: 237 triples, 20 concepts, no S27 violations, no
mapping relations used intra-scheme, no mapping target that is not a
`skos:Concept`, exactly one `skos:prefLabel` and one `skos:definition` per
concept, and no instance token mapping to more than one concept.

## Explicitly out of scheme

VSS instance tokens that look positional but are not, listed in the file so the
vocabulary is not misapplied to them:

| Token | Why not |
|---|---|
| `Low` / `High` | `Body.Lights.Beam` — beam *type*, not height |
| `Primary` / `Secondary` | `Body.WiperSystem` — functional role |
| `Trunk` | `Vehicle.ControlUnit` — a compartment, i.e. part-whole membership. It already exists as a concept under `VehiclePhysicalMembership` in the sibling example, which is exactly where it belongs |
| `Sensor`, `PID` | not positions in any sense |

`Trunk` is the clearest argument for the multi-scheme pattern over a single flat
taxonomy: the same token is in scope for one facet and out of scope for another.

## Binding to VSS

Concepts are additionally typed as `vsso:PositionInVehicle` individuals. That
class exists in [VSSo](https://github.com/w3c/vsso) (`spec/vsso-core.ttl`),
is reached by `vsso:postionedAt`, and currently **has no individuals at all** —
its only labelling mechanism is `vsso:positionName`, an uncontrolled
`xsd:string`. A concept scheme is a direct fit for that gap.

```turtle
<…/Cabin/Seat/Row2/DriverSide> vsso:postionedAt vsspos:DriverSide .
<…/myVehicle> schema:steeringPosition schema:RightHandDriving .
# ⇒ that seat's position resolves to vsspos:Right
```

> [!WARNING]
> Two caveats on this binding. The misspelling in `vsso:postionedAt` is in the
> published ontology and must be used verbatim. And VSSo is effectively dormant:
> last commit 2024-02-21, with the generated spec tracking VSS 2.2 against a
> current v6.1. Binding to it only pays off if something maintains it, and no
> COVESA-hosted successor repository currently exists — which may itself be
> worth raising.

## Files

| File | Contents |
|---|---|
| `skos.ttl` | The concept scheme — 20 concepts, 3 collections, 3 annotation properties |

## Open questions for reviewers

1. Is `examples/` the right home, or does this belong outside the S2DM
   repository under the note in [`CONTRIBUTING.md`](../../CONTRIBUTING.md) about
   domain data specifications? It is offered here as a demonstration of the
   pattern rather than as a specification, but the line is a fair one to draw
   differently.
2. Should `vssInstanceToken`, `axialOrientation` and `resolvesVia` be
   scheme-local annotation properties as they are here, or does S2DM want a
   general mechanism for "this concept corresponds to these source-model
   tokens"? The first is a recurring need for any scheme layered over an
   existing model.
3. `Upper` / `Lower` are included for axis completeness but no VSS v6.1 token
   maps to them. Keep, or drop until something needs them?
