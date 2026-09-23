import type { Database } from "sql.js";

export type SearchOptions = {
	caseSensitive: boolean;
	regex: boolean;
	wholeWord: boolean;
};

export const DEFAULT_SEARCH_OPTIONS: SearchOptions = {
	regex: false,
	wholeWord: false,
	caseSensitive: false,
};

export const MATCH_FUNCTION = "s2dm_match";

function isAscii(value: string): boolean {
	for (const character of value) {
		if ((character.codePointAt(0) ?? 0) > 0x7f) {
			return false;
		}
	}
	return true;
}

function escapeRegExp(value: string): string {
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

	if (options.regex || options.wholeWord) {
		// The needle is a pattern only where regex is asked for; otherwise it is
		// literal text that happens to need the same machinery.
		const source = options.regex ? needle : escapeRegExp(needle);
		// Not \b, which JavaScript defines over [A-Za-z0-9_] only.
		const bounded = options.wholeWord
			? `(?<![\\p{L}\\p{N}_])(?:${source})(?![\\p{L}\\p{N}_])`
			: source;
		// Only where \p{…} needs it: unicode mode also rejects escapes a written
		// pattern may legally use, such as \- outside a character class.
		const unicode = options.wholeWord ? "u" : "";
		try {
			new RegExp(bounded, `${flags}${unicode}`);
		} catch (error) {
			const detail = error instanceof Error ? error.message : String(error);
			throw new Error(`Invalid regular expression: ${detail}`);
		}
		return { kind: "regexp", source: bounded, flags: `${flags}${unicode}` };
	}

	// SQLite's LIKE folds case for ASCII only, so anything else takes the regex
	// path to agree with the other modes.
	if (!options.caseSensitive && !isAscii(needle)) {
		return { kind: "regexp", source: escapeRegExp(needle), flags: "i" };
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
