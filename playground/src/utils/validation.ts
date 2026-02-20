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

export function isGraphQLFile(filename: string): boolean {
	return filename.endsWith(".graphql") || filename.endsWith(".gql");
}
