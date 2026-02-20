const JSON_LANGUAGE_ALIASES = new Set([
	"json-ld",
	"jsonld",
	"application/ld+json",
	"ld+json",
	"avsc",
]);

export function resolveMonacoLanguage(inputLanguage: string): string {
	const normalizedLanguage = inputLanguage.trim().toLowerCase();

	if (JSON_LANGUAGE_ALIASES.has(normalizedLanguage)) {
		return "json";
	}

	return normalizedLanguage;
}
