import {
	FileText,
	History,
	Link,
	type LucideIcon,
	Shapes,
	Table,
} from "lucide-react";

// Chosen for what each ModL table holds: concepts are the model's shapes,
// revisions its history, contracts the documented agreements, bindings the links
// to runtime-addressable paths. Anything else falls back to a plain table.
const TABLE_ICONS: Record<string, LucideIcon> = {
	concepts: Shapes,
	revisions: History,
	contracts: FileText,
	bindings: Link,
};

export function tableIcon(table: string): LucideIcon {
	return TABLE_ICONS[table.toLowerCase()] ?? Table;
}
