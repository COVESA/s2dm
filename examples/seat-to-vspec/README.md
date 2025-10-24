# Example: Exporting to VSPEC
Consider the `Seat` branch as specified by the Vehicle Signal Specification (VSS).
> For easiness, the whole `Seat` reference has been made available in one file called `expected.vspec` in this directory.

The correspondance in the GraphQL SDL is available in the folder `/modular_seat_spec`.

By calling the exporter:
```bash
s2dm export vspec -s modular_seat_spec -o result.vspec
```

We obtain the `Seat` in the original `VSPEC` format.
See `result.vspec`.
This file can be used with the exiting `vss-tools`.
## Currently known limitations
> TODO: Fix some minor details when it comes to naming conventions.

> TODO: Define how the features that are not part of the `VSPEC` feature set are to be mapped or at least logged. For example, cross-references, and types enums structures that correspoind to the intended `allowed` values in `VSPEC`.
