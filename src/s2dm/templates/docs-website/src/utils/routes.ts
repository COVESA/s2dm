/**
 * Returns the address of a page under a root.
 *
 * @param root - The root address, with or without a trailing slash.
 * @param segment - The page's segment, or `null` for the page at the root.
 * @returns The root, or the root followed by the segment.
 */
export function routePath(root: string, segment: string | null): string {
	const base = root.replace(/\/$/, "");
	if (segment === null) {
		return base;
	}
	return `${base}/${segment}`;
}

/**
 * Returns the segment of an address under a root.
 *
 * @param pathname - The address to read.
 * @param root - The root address, with or without a trailing slash.
 * @returns `""` for the root itself, the segment for an address below it, or
 *   `null` for any other address.
 */
export function routeSegment(pathname: string, root: string): string | null {
	const base = root.replace(/\/$/, "");
	const path = pathname.replace(/\/$/, "");
	if (path === base) {
		return "";
	}
	if (!path.startsWith(`${base}/`)) {
		return null;
	}
	const segment = path.slice(base.length + 1);
	if (segment === "") {
		return null;
	}
	return segment;
}
