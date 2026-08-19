export type PredefinedQuery = {
	label: string;
	description: string;
	sql: string;
};

export const PREDEFINED_QUERIES: PredefinedQuery[] = [
	{
		label: "Concept inventory",
		description: "How many concepts of each kind, split by status",
		sql: `SELECT kind, status, COUNT(*) AS concepts
FROM concepts
GROUP BY kind, status
ORDER BY kind, status;`,
	},
	{
		label: "Full chain",
		description: "Concept to revision to contract to binding, end to end",
		sql: `SELECT
  c.current_label AS concept,
  c.kind,
  r.revision_uri AS revision,
  ct.contract_uri AS contract,
  b.binding_uri AS binding,
  b.instance_label AS instance
FROM concepts c
LEFT JOIN revisions r  ON r.concept_uri   = c.concept_uri
LEFT JOIN contracts ct ON ct.revision_uri = r.revision_uri
LEFT JOIN bindings b   ON b.contract_uri  = ct.contract_uri
ORDER BY c.serial, r.serial, ct.serial, b.serial;`,
	},
	{
		label: "Revision history",
		description: "Concepts revised more than once, newest revision last",
		sql: `SELECT
  c.current_label AS concept,
  COUNT(r.revision_uri) AS revisions,
  SUM(r.status = 'ACTIVE') AS active,
  SUM(r.status = 'SUPERSEDED') AS superseded
FROM concepts c
JOIN revisions r ON r.concept_uri = c.concept_uri
GROUP BY c.concept_uri
HAVING COUNT(r.revision_uri) > 1
ORDER BY revisions DESC, concept;`,
	},
	{
		label: "Revision chain",
		description: "Walk previous_revision_uri to show each concept's lineage",
		sql: `WITH RECURSIVE chain(revision_uri, concept_uri, status, depth) AS (
  SELECT revision_uri, concept_uri, status, 0
  FROM revisions
  WHERE previous_revision_uri IS NULL
  UNION ALL
  SELECT r.revision_uri, r.concept_uri, r.status, chain.depth + 1
  FROM revisions r
  JOIN chain ON r.previous_revision_uri = chain.revision_uri
)
SELECT c.current_label AS concept, chain.depth, chain.revision_uri, chain.status
FROM chain
JOIN concepts c ON c.concept_uri = chain.concept_uri
ORDER BY concept, depth;`,
	},
	{
		label: "Instance expansion",
		description: "Contracts that expanded into more than one binding",
		sql: `SELECT
  c.current_label AS concept,
  ct.contract_uri AS contract,
  COUNT(b.binding_uri) AS bindings,
  GROUP_CONCAT(b.instance_label, ', ') AS instances
FROM contracts ct
JOIN concepts c ON c.concept_uri = ct.concept_uri
JOIN bindings b ON b.contract_uri = ct.contract_uri
GROUP BY ct.contract_uri
HAVING COUNT(b.binding_uri) > 1
ORDER BY bindings DESC, concept;`,
	},
	{
		label: "Not active",
		description: "Every superseded or removed record, across all four tables",
		sql: `SELECT 'concept' AS record, concept_uri AS uri, status FROM concepts WHERE status <> 'ACTIVE'
UNION ALL
SELECT 'revision', revision_uri, status FROM revisions WHERE status <> 'ACTIVE'
UNION ALL
SELECT 'contract', contract_uri, status FROM contracts WHERE status <> 'ACTIVE'
UNION ALL
SELECT 'binding', binding_uri, status FROM bindings WHERE status <> 'ACTIVE'
ORDER BY record, uri;`,
	},
	{
		label: "Renamed concepts",
		description: "Concepts carrying earlier labels",
		sql: `SELECT current_label AS concept, previous_labels, kind, status
FROM concepts
WHERE previous_labels IS NOT NULL
ORDER BY concept;`,
	},
	{
		label: "Concept hierarchy",
		description: "Nesting implied by parent_uri, deepest last",
		sql: `WITH RECURSIVE tree(concept_uri, label, depth) AS (
  SELECT concept_uri, current_label, 0
  FROM concepts
  WHERE parent_uri IS NULL
  UNION ALL
  SELECT c.concept_uri, c.current_label, tree.depth + 1
  FROM concepts c
  JOIN tree ON c.parent_uri = tree.concept_uri
)
SELECT depth, label AS concept, concept_uri
FROM tree
ORDER BY depth, concept;`,
	},
	{
		label: "Chains that stop early",
		description: "Revisions with no contract, and contracts with no binding",
		sql: `SELECT 'revision without contract' AS gap, r.revision_uri AS uri, c.current_label AS concept
FROM revisions r
JOIN concepts c ON c.concept_uri = r.concept_uri
WHERE NOT EXISTS (SELECT 1 FROM contracts ct WHERE ct.revision_uri = r.revision_uri)
UNION ALL
SELECT 'contract without binding', ct.contract_uri, c.current_label
FROM contracts ct
JOIN concepts c ON c.concept_uri = ct.concept_uri
WHERE NOT EXISTS (SELECT 1 FROM bindings b WHERE b.contract_uri = ct.contract_uri)
ORDER BY gap, uri;`,
	},
];
