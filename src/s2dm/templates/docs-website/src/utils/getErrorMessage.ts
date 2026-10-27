/**
 * Read the message of a thrown value.
 *
 * @param error - The thrown value.
 * @returns The error's message, or the value as text when it is not an `Error`.
 */
export function getErrorMessage(error: unknown): string {
	if (error instanceof Error) {
		return error.message;
	}
	return String(error);
}
