export const API_BASE_URL =
	import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
export const API_TIMEOUT = 30000;
/** Axios treats a timeout of 0 as no timeout. */
export const NO_TIMEOUT = 0;
