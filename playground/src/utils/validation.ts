export function isValidUrl(url: string): boolean {
	if (!url.trim()) {
		return false;
	}

	try {
		new URL(url);
		return true;
	} catch {
		return false;
	}
}

/**
 * Tells what is wrong with a URL that the user typed.
 *
 * @param url The typed URL, already trimmed.
 * @returns The error message, or an empty string for a valid URL.
 */
export function getUrlError(url: string): string {
	if (!url) {
		return "URL is required";
	}
	if (!isValidUrl(url)) {
		return "Please enter a valid URL";
	}

	return "";
}

export function isGraphQLFile(filename: string): boolean {
	return filename.endsWith(".graphql") || filename.endsWith(".gql");
}
