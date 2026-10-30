/**
 * Fetch a JSON file.
 *
 * @param url - The file's URL.
 * @param init - Request options, e.g. an abort `signal`.
 * @returns The parsed JSON.
 * @throws Error when the response status is not OK.
 */
export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
	const response = await fetch(url, init);
	if (!response.ok) {
		throw new Error(`Fetching ${url} failed with status ${response.status}.`);
	}
	return response.json() as Promise<T>;
}
