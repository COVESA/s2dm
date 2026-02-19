import axios, {
	type AxiosInstance,
	type InternalAxiosRequestConfig,
} from "axios";
import { API_BASE_URL, API_TIMEOUT } from "@/config/api";

class ApiClient {
	private client: AxiosInstance;
	private requestTimings: Map<InternalAxiosRequestConfig, number>;

	constructor(baseURL: string = API_BASE_URL, timeout: number = API_TIMEOUT) {
		this.requestTimings = new Map();

		this.client = axios.create({
			baseURL,
			timeout,
			headers: {
				"Content-Type": "application/json",
			},
		});

		this.client.interceptors.request.use((config) => {
			this.requestTimings.set(config, Date.now());
			console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
			return config;
		});

		this.client.interceptors.response.use(
			(response) => {
				const startTime = this.requestTimings.get(response.config);
				if (startTime) {
					const duration = Date.now() - startTime;
					console.log(
						`[API] ${response.config.method?.toUpperCase()} ${response.config.url} - ${response.status} (${duration}ms)`,
					);
					this.requestTimings.delete(response.config);
				}
				return response;
			},
			(error) => {
				if (error.config) {
					const startTime = this.requestTimings.get(error.config);
					if (startTime) {
						const duration = Date.now() - startTime;
						console.error(
							`[API] ${error.config.method?.toUpperCase()} ${error.config.url} - Failed (${duration}ms)`,
							error.message,
						);
						this.requestTimings.delete(error.config);
					}
				}
				return Promise.reject(error);
			},
		);
	}

	async get<T>(endpoint: string): Promise<T> {
		const response = await this.client.get<T>(endpoint);
		return response.data;
	}

	async post<T>(endpoint: string, data?: unknown): Promise<T> {
		const response = await this.client.post<T>(endpoint, data);
		return response.data;
	}
}

export const apiClient = new ApiClient();
