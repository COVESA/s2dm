export const LEDGER_PAGE_SIZE = 50;

export const EXPLORE_PREVIEW_LIMIT = 5;

export const CHAIN_GROUP_RENDER_LIMIT = 5;

export const CHAIN_GROUP_FETCH_LIMIT = 100;

// Descendants multiply per level, so the walk stops expanding after this many
// nodes. Groups past it still list their rows, without their own children.
export const CHAIN_NODE_BUDGET = 300;

// Levels opened automatically below the selected record. Three reaches bindings
// from a concept, which is the full chain.
export const CHAIN_AUTO_EXPAND_DEPTH = 3;

export const FILTERABLE_COLUMNS = ["kind", "status"] as const;
