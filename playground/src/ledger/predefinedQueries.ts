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
		description: "Two references per row, with the label to read them by",
		sql: `SELECT c.current_label, c.concept_uri, r.revision_uri, r.status
FROM concepts c
JOIN revisions r ON r.concept_uri = c.concept_uri;`,
	},
	{
		label: "Labels only",
		description: "No URIs, so a selected row offers no actions",
		sql: "SELECT current_label, kind, status FROM concepts;",
	},
	{
		label: "Row counts",
		description: "An aggregate: one row, but not a record",
		sql: `SELECT 'concepts' AS table_name, COUNT(*) AS rows FROM concepts
UNION ALL SELECT 'revisions', COUNT(*) FROM revisions
UNION ALL SELECT 'contracts', COUNT(*) FROM contracts
UNION ALL SELECT 'bindings',  COUNT(*) FROM bindings;`,
	},
	{
		label: "Write attempt",
		description: "Rejected: the database is opened read-only",
		sql: "DELETE FROM concepts;",
	},
];
