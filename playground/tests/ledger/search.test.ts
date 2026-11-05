import {
	compileSearchPattern,
	DEFAULT_SEARCH_OPTIONS,
	type SearchPattern,
} from "@ledger-ui/data/search";
import {
	columnPredicate,
	escapeLikePattern,
} from "@ledger-ui/data/searchPredicate";
import { describe, expect, it } from "vitest";

function regexOf(pattern: SearchPattern): RegExp {
	if (pattern.kind !== "regexp") {
		throw new Error(`Expected a regexp pattern, got ${pattern.kind}`);
	}
	return new RegExp(pattern.source, pattern.flags);
}

describe("compileSearchPattern", () => {
	it("uses LIKE by default", () => {
		const pattern = compileSearchPattern("car", DEFAULT_SEARCH_OPTIONS);

		expect(pattern).toEqual({ kind: "like", value: "car" });
	});

	it("uses instr when the case must match", () => {
		const options = { ...DEFAULT_SEARCH_OPTIONS, caseSensitive: true };

		const pattern = compileSearchPattern("Car", options);

		expect(pattern).toEqual({ kind: "instr", value: "Car" });
	});

	it("uses a regex for non-ASCII text that ignores case", () => {
		const pattern = compileSearchPattern("Größe", DEFAULT_SEARCH_OPTIONS);
		const regex = regexOf(pattern);
		const isMatch = regex.test("größe");

		expect(isMatch).toBe(true);
	});

	it("treats the needle as a pattern with the regex option", () => {
		const options = { ...DEFAULT_SEARCH_OPTIONS, regex: true };

		const pattern = compileSearchPattern("Fr.nt", options);
		const regex = regexOf(pattern);
		const isMatch = regex.test("Front");

		expect(isMatch).toBe(true);
	});

	it("treats the needle as text with only the whole-word option", () => {
		const options = { ...DEFAULT_SEARCH_OPTIONS, wholeWord: true };

		const pattern = compileSearchPattern("a.c", options);
		const regex = regexOf(pattern);
		const matchesText = regex.test("x a.c y");
		const matchesOtherText = regex.test("x abc y");

		expect(matchesText).toBe(true);
		expect(matchesOtherText).toBe(false);
	});

	it("matches whole words only with the whole-word option", () => {
		const options = { ...DEFAULT_SEARCH_OPTIONS, wholeWord: true };

		const pattern = compileSearchPattern("Front", options);
		const regex = regexOf(pattern);
		const matchesWord = regex.test("Front left");
		const matchesLongerWord = regex.test("Frontal");

		expect(matchesWord).toBe(true);
		expect(matchesLongerWord).toBe(false);
	});

	it("rejects an invalid regex", () => {
		const options = { ...DEFAULT_SEARCH_OPTIONS, regex: true };

		expect(() => compileSearchPattern("(", options)).toThrow(Error);
	});
});

describe("escapeLikePattern", () => {
	it("escapes the LIKE wildcards and the escape character", () => {
		const escaped = escapeLikePattern("50%_a\\b");

		expect(escaped).toBe("50\\%\\_a\\\\b");
	});
});

describe("columnPredicate", () => {
	it("wraps an escaped LIKE value in wildcards", () => {
		const predicate = columnPredicate('"label"', {
			kind: "like",
			value: "50%",
		});

		expect(predicate.params).toEqual(["%50\\%%"]);
	});

	it("passes the regex source and flags", () => {
		const pattern: SearchPattern = {
			kind: "regexp",
			source: "a.c",
			flags: "i",
		};

		const predicate = columnPredicate('"label"', pattern);

		expect(predicate.params).toEqual(["a.c", "i"]);
	});
});
