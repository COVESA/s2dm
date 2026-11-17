/**
 * Fetch a file.
 *
 * @param url - The file's URL.
 * @param init - Request options, e.g. an abort `signal`.
 * @returns The response.
 * @throws Error when the response status is not OK.
 */
async function fetchFile(url: string, init?: RequestInit): Promise<Response> {
	const response = await fetch(url, init);
	if (!response.ok) {
		throw new Error(`Fetching ${url} failed with status ${response.status}.`);
	}
	return response;
}

/**
 * Fetch a JSON file.
 *
 * @param url - The file's URL.
 * @param init - Request options, e.g. an abort `signal`.
 * @returns The parsed JSON.
 * @throws Error when the response status is not OK.
 */
export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
	const response = await fetchFile(url, init);
	return response.json() as Promise<T>;
}

/**
 * Fetch a text file.
 *
 * @param url - The file's URL.
 * @param init - Request options, e.g. an abort `signal`.
 * @returns The file's text.
 * @throws Error when the response status is not OK.
 */
export async function fetchText(url: string, init?: RequestInit): Promise<string> {
	const response = await fetchFile(url, init);
	return response.text();
}
