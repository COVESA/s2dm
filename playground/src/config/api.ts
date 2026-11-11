export const API_BASE_URL =
	import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
export const API_TIMEOUT = 30000;
/** The API client sets no timeout for a timeout of 0. */
export const NO_TIMEOUT = 0;
