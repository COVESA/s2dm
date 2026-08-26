import type { Database } from "sql.js";

export type SearchMode = "substring" | "wholeWord" | "regex";

export type SearchOptions = {
	mode: SearchMode;
	caseSensitive: boolean;
};

export const DEFAULT_SEARCH_OPTIONS: SearchOptions = {
	mode: "substring",
	caseSensitive: false,
};

export const MATCH_FUNCTION = "s2dm_match";

export function escapeRegExp(value: string): string {
	return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export type SearchPattern =
	| { kind: "like"; value: string }
	| { kind: "instr"; value: string }
	| { kind: "regexp"; source: string; flags: string };

export function compileSearchPattern(
	needle: string,
	options: SearchOptions,
): SearchPattern {
	const flags = options.caseSensitive ? "" : "i";

	if (options.mode === "regex") {
		try {
			new RegExp(needle, flags);
		} catch (error) {
			const detail = error instanceof Error ? error.message : String(error);
			throw new Error(`Invalid regular expression: ${detail}`);
		}
		return { kind: "regexp", source: needle, flags };
	}

	if (options.mode === "wholeWord") {
		return { kind: "regexp", source: `\\b${escapeRegExp(needle)}\\b`, flags };
	}

	// LIKE is case-insensitive for ASCII and instr is not, so between them the
	// common modes avoid a JavaScript callback per row.
	return options.caseSensitive
		? { kind: "instr", value: needle }
		: { kind: "like", value: needle };
}

export function registerSearchFunction(database: Database): void {
	const compiled = new Map<string, RegExp>();

	database.create_function(
		MATCH_FUNCTION,
		(source: string, value: unknown, flags: string) => {
			if (value === null || value === undefined) {
				return 0;
			}
			const key = `${flags} ${source}`;
			let expression = compiled.get(key);
			if (!expression) {
				expression = new RegExp(source, flags);
				compiled.set(key, expression);
			}
			return expression.test(String(value)) ? 1 : 0;
		},
	);
}
