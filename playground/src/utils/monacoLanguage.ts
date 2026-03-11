const JSON_LANGUAGE_ALIASES = new Set([
	"json-ld",
	"jsonld",
	"avsc",
]);

const TURTLE_LANGUAGE_ALIASES = new Set([
	"ttl",
	"turtle",
]);

export function resolveMonacoLanguage(inputLanguage: string): string {
	const normalizedLanguage = inputLanguage.trim().toLowerCase();

	if (JSON_LANGUAGE_ALIASES.has(normalizedLanguage)) {
		return "json";
	}

	if (TURTLE_LANGUAGE_ALIASES.has(normalizedLanguage)) {
		return "turtle";
	}

	return normalizedLanguage;
}
