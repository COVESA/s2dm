export type PredefinedQuery = {
	label: string;
	description: string;
	sql: string;
};

export const PREDEFINED_QUERIES: PredefinedQuery[] = [
	{
		label: "One concept",
		description: "A single whole record, so its details open on their own",
		sql: "SELECT * FROM concepts LIMIT 1;",
	},
	{
		label: "All concepts",
		description: "Whole records, so any row can be shown in Raw Tables",
		sql: "SELECT * FROM concepts;",
	},
	{
		label: "All bindings",
		description: "Whole records that also point at their contract",
		sql: "SELECT * FROM bindings;",
	},
	{
		label: "Chain URIs",
		description:
			"Four references per row: concept, revision, contract, binding",
		sql: `SELECT
  c.concept_uri,
  r.revision_uri,
  ct.contract_uri,
  b.binding_uri
FROM concepts c
JOIN revisions r  ON r.concept_uri   = c.concept_uri
JOIN contracts ct ON ct.revision_uri = r.revision_uri
JOIN bindings b   ON b.contract_uri  = ct.contract_uri;`,
	},
	{
		label: "Revisions per concept",
		description:
			"Two references per row, with the label and the changes of each revision",
		sql: `SELECT c.current_label, c.concept_uri, r.revision_uri, r.status,
  a.aspect_key, a.operation, a.newer_value
FROM concepts c
JOIN revisions r ON r.concept_uri = c.concept_uri
LEFT JOIN revision_aspects a ON a.revision_uri = r.revision_uri;`,
	},
	{
		label: "Bindings by runtime path",
		description:
			"Instance tags read with json_each: one row per dimension, one row for a singleton",
		sql: `SELECT
  binding.runtime_path,
  entity.current_label AS entity,
  dimension.key AS dimension,
  dimension.value AS instance,
  binding.status,
  binding.binding_uri
FROM bindings binding
LEFT JOIN json_each(binding.instance_tags) AS tag
LEFT JOIN json_each(tag.value) AS dimension
LEFT JOIN concepts entity ON entity.concept_uri = tag.key
ORDER BY binding.runtime_path, dimension.key;`,
	},
	{
		label: "Labels only",
		description: "No URIs, so a selected row offers no actions",
		sql: "SELECT current_label, kind, status, instances FROM concepts;",
	},
	{
		label: "Row counts",
		description: "An aggregate: one row, but not a record",
		sql: `SELECT 'concepts' AS table_name, COUNT(*) AS rows FROM concepts
UNION ALL SELECT 'revisions', COUNT(*) FROM revisions
UNION ALL SELECT 'contracts', COUNT(*) FROM contracts
UNION ALL SELECT 'bindings', COUNT(*) FROM bindings
UNION ALL SELECT 'revision_aspects', COUNT(*) FROM revision_aspects
UNION ALL SELECT 'contract_references', COUNT(*) FROM contract_references;`,
	},
	{
		label: "Write attempt",
		description: "Rejected: the database is opened read-only",
		sql: "DELETE FROM concepts;",
	},
];
