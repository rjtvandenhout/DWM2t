# Breeding mode identification

The internal byte used by the breeding routine is read at `D7F1` during the call.

## Mode 2 = link-cable breeding

At `0E:56D1` the recipe parser encounters the `FB` delimiter. The parser continues beyond that delimiter only when `D7F1 == 2`.

The public breeding-data documentation independently identifies `FB FB` as the marker after which recipe sets are link-cable-only. The same mode also unlocks the corresponding special family marker at `0E:575F`.

Therefore mode `2` can be identified directly as link breeding.

## Mode 1 = finalized local breeding

A separate caller sets `D7F1 = 1` immediately before invoking the child-construction routine. The resulting path uses the pedigree/base parent's plus, adds the level-sum plus bonus, applies the hidden +3 percentage-point finalized-breeding stat bonus, and advances the breeding state machine.

This matches documented local breeding behavior where pluses accumulate from the pedigree/base monster.

## Mode 0 = preview/query path

Another caller clears `D7F1` before invoking the same routine, then immediately consumes the calculated result IDs for validation/display logic rather than following the finalized path. In this mode the temporary plus base is `max(parent1_plus, parent2_plus)` and the +3 finalized-breeding stat component is omitted.

I label this `preview/query` rather than assigning a player-facing menu name, because the exact UI label is not encoded in the routine itself.
