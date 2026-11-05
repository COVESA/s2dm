import {
	Diff,
	FileSymlink,
	FileText,
	History,
	Link,
	type LucideIcon,
	Shapes,
	Table,
} from "lucide-react";

// Chosen for what each ModL table holds: concepts are the model's shapes,
// revisions its history, contracts the documented agreements, bindings the links
// to runtime-addressable paths, revision aspects what a revision changed, and
// contract references the links from one contract to another. Anything else
// falls back to a plain table.
const TABLE_ICONS: Record<string, LucideIcon> = {
	concepts: Shapes,
	revisions: History,
	contracts: FileText,
	bindings: Link,
	revision_aspects: Diff,
	contract_references: FileSymlink,
};

export function tableIcon(table: string): LucideIcon {
	return TABLE_ICONS[table.toLowerCase()] ?? Table;
}
