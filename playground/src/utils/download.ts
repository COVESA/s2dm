/**
 * Downloads text content as a file
 * @param content The text content to download
 * @param fileName The name of the file to download
 */
export function downloadTextFile(content: string, fileName: string): void {
	const blob = new Blob([content], { type: "text/plain" });
	const url = URL.createObjectURL(blob);
	const anchor = document.createElement("a");
	anchor.href = url;
	anchor.download = fileName;
	anchor.click();
	URL.revokeObjectURL(url);
}
