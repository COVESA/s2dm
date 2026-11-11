import { API_BASE_URL, API_TIMEOUT } from "@/config/api";
import { getErrorMessage } from "@/utils/getErrorMessage";

export const GENERIC_ERROR_MESSAGE =
	"We couldn't complete that request. Please try again.";
const TIMEOUT_ERROR_MESSAGE = "The API request timed out";
const UNREACHABLE_ERROR_MESSAGE = "Cannot reach the API server";

/** A failed API request. The message is ready to show to the user. */
export class ApiError extends Error {
	public status: number | undefined;

	/**
	 * @param message The message to show to the user.
	 * @param status The HTTP status of the error reply. It is undefined when no
	 * reply arrived.
	 */
	constructor(message: string, status?: number) {
		super(message);
		this.name = "ApiError";
		this.status = status;
	}
}

/**
 * Reads a response body as JSON.
 *
 * @param response The response to read.
 * @returns The parsed body, or undefined when the body is empty.
 */
async function readJsonBody(response: Response): Promise<unknown> {
	const bodyText = await response.text();
	if (bodyText === "") {
		return undefined;
	}

	return JSON.parse(bodyText);
}

/**
 * Reads the message to show for an HTTP error reply.
 *
 * @param response The error reply.
 * @returns The API's message, or a generic message when the reply has none.
 */
async function readErrorMessage(response: Response): Promise<string> {
	let body: unknown;
	try {
		body = await readJsonBody(response);
	} catch (error) {
		if (error instanceof SyntaxError) {
			return GENERIC_ERROR_MESSAGE;
		}

		throw error;
	}

	if (typeof body !== "object" || body === null || !("message" in body)) {
		return GENERIC_ERROR_MESSAGE;
	}

	const { message } = body;
	if (typeof message !== "string" || message.trim().length === 0) {
		return GENERIC_ERROR_MESSAGE;
	}

	return message;
}

/**
 * Turns an error from a request into an API error when it comes from the
 * network.
 *
 * @param error The error that the request threw.
 * @returns A timeout error when the timeout fired, an unreachable-server
 * error when the network failed, or the given error otherwise.
 */
function toRequestError(error: unknown): unknown {
	if (error instanceof DOMException && error.name === "TimeoutError") {
		return new ApiError(TIMEOUT_ERROR_MESSAGE);
	}

	if (error instanceof TypeError) {
		return new ApiError(UNREACHABLE_ERROR_MESSAGE);
	}

	return error;
}

class ApiClient {
	private baseURL: string;
	private timeout: number;

	constructor(baseURL: string = API_BASE_URL, timeout: number = API_TIMEOUT) {
		this.baseURL = baseURL;
		this.timeout = timeout;
	}

	async get<T>(endpoint: string): Promise<T> {
		return this.request<T>("GET", endpoint);
	}

	async post<T>(
		endpoint: string,
		data?: unknown,
		timeout?: number,
	): Promise<T> {
		return this.request<T>("POST", endpoint, data, timeout);
	}

	/**
	 * Sends a request and reads its JSON reply.
	 *
	 * @param method The HTTP method.
	 * @param endpoint The path below the base URL.
	 * @param data The request body, sent as JSON.
	 * @param timeout The timeout in milliseconds. A timeout of 0 sets no
	 * timeout. The client's default timeout applies when it is undefined.
	 * @returns The parsed reply body, or undefined when the reply has no body.
	 */
	private async request<T>(
		method: string,
		endpoint: string,
		data?: unknown,
		timeout: number = this.timeout,
	): Promise<T> {
		const url = `${this.baseURL}${endpoint}`;
		const init: RequestInit = { method };
		if (data !== undefined) {
			init.headers = { "Content-Type": "application/json" };
			init.body = JSON.stringify(data);
		}

		if (timeout > 0) {
			init.signal = AbortSignal.timeout(timeout);
		}

		console.log(`[API] ${method} ${endpoint}`);
		const startTime = Date.now();
		try {
			const response = await fetch(url, init);
			if (!response.ok) {
				const errorMessage = await readErrorMessage(response);
				throw new ApiError(errorMessage, response.status);
			}

			const body = await readJsonBody(response);
			const duration = Date.now() - startTime;
			console.log(
				`[API] ${method} ${endpoint} - ${response.status} (${duration}ms)`,
			);
			return body as T;
		} catch (error) {
			const requestError = toRequestError(error);
			const duration = Date.now() - startTime;
			const errorMessage = getErrorMessage(requestError);
			console.error(
				`[API] ${method} ${endpoint} - Failed (${duration}ms)`,
				errorMessage,
			);
			throw requestError;
		}
	}
}

export const apiClient = new ApiClient();
