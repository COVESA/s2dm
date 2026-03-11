import type { Monaco } from "@monaco-editor/react";

export const registerTurtle = (monaco: Monaco) => {
	const id = "turtle";

	monaco.languages.register({
		id,
		extensions: [".ttl"],
		aliases: ["Turtle", "turtle", "ttl"],
		mimetypes: ["text/turtle", "application/x-turtle"],
	});

	monaco.languages.setLanguageConfiguration(id, {
		comments: { lineComment: "#" },
		brackets: [
			["{", "}"],
			["[", "]"],
			["(", ")"],
		],
		autoClosingPairs: [
			{ open: "{", close: "}" },
			{ open: "[", close: "]" },
			{ open: "(", close: ")" },
			{ open: '"', close: '"', notIn: ["string", "comment"] },
			{ open: "'", close: "'", notIn: ["string", "comment"] },
		],
		surroundingPairs: [
			{ open: "{", close: "}" },
			{ open: "[", close: "]" },
			{ open: "(", close: ")" },
			{ open: '"', close: '"' },
			{ open: "'", close: "'" },
		],
	});

	// 3) Syntax highlighting (Monarch tokenizer)
	monaco.languages.setMonarchTokensProvider(id, {
		defaultToken: "",
		tokenPostfix: ".ttl",

		// Common regex fragments
		// PN_* is simplified here to keep it fast and robust in Monarch.
		// It's not a full W3C Turtle grammar, but covers real-world TTL well.
		tokenizer: {
			root: [
				// Comments
				[/#.*$/, "comment"],

				// Directives (Turtle & SPARQL-style)
				[/@(?:prefix|base)\b/, "keyword.directive"],
				[/\b(?:PREFIX|BASE)\b/, "keyword.directive"],

				// Abbreviation for rdf:type
				[/\b(a)\b/, "keyword"],

				// Booleans
				[/\b(true|false)\b/, "literal.boolean"],

				// Datatype marker and language tag
				[/\^\^/, "operator"],
				[/@[a-zA-Z]+(-[a-zA-Z0-9]+)*/, "literal.language"],

				// IRIREF: <...>
				[/<[^<>"{}|^`\\\s]*>/, "string.link"],

				// Blank node labels: _:abc
				[/_[ \t]*:/, "invalid"], // helps catch `_ :` mistakes
				[/_:\w[\w.-]*/, "type.identifier"],

				// Prefixed names (simplified):
				// prefix:local or :local
				[/[A-Za-z][\w.-]*:/, "type.namespace"], // "ex:"
				[/:([\w.-]+)?/, "type.namespace"], // ":local" or ":" (rare)
				[/[A-Za-z][\w.-]*:[\w.-]+/, "identifier"],

				// Numbers (integer/decimal/double)
				[/[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?\b/, "number.float"],
				[/[+-]?\d+[eE][+-]?\d+\b/, "number.float"],
				[/[+-]?\d+\b/, "number"],

				// Punctuation significant in Turtle
				[/[.;,]/, "delimiter"],
				[/[[\](){}]/, "@brackets"],

				// Strings (short and long)
				[/"""/, { token: "string", next: "@tripleDq" }],
				[/'''/, { token: "string", next: "@tripleSq" }],
				[/"/, { token: "string", next: "@dqString" }],
				[/'/, { token: "string", next: "@sqString" }],

				// Prefix/base declarations often contain a trailing '.'
				// (already covered by delimiter)

				// Anything else
				[/\s+/, "white"],
			],

			dqString: [
				[/\\./, "string.escape"],
				[/[^\\"]+/, "string"],
				[/"/, { token: "string", next: "@pop" }],
			],

			sqString: [
				[/\\./, "string.escape"],
				[/[^\\']+/, "string"],
				[/'/, { token: "string", next: "@pop" }],
			],

			tripleDq: [
				[/\\./, "string.escape"],
				[/[^\\"]+/, "string"],
				[/"""/, { token: "string", next: "@pop" }],
				[/"/, "string"], // allow embedded quotes
			],

			tripleSq: [
				[/\\./, "string.escape"],
				[/[^\\']+/, "string"],
				[/'''/, { token: "string", next: "@pop" }],
				[/'/, "string"], // allow embedded quotes
			],
		},
	});
};
