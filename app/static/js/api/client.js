/**
 * Centralized API Client Module (Phase 8A)
 * Provides a lightweight wrapper around HTTP fetch() with automatic JSON handling,
 * credentials management, FormData file uploads, and uniform error reporting.
 */
class ApiClient {
    constructor(baseURL = "") {
        this.baseURL = baseURL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;

        const defaultHeaders = {};
        if (!(options.body instanceof FormData)) {
            defaultHeaders["Content-Type"] = "application/json";
        }

        const config = {
            credentials: "include",
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers,
            },
        };

        if (options.body && !(options.body instanceof FormData) && typeof options.body === "object") {
            config.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, config);

            // Handle non-OK response codes
            if (!response.ok) {
                let errorMessage = `Erreur HTTP ${response.status} (${response.statusText})`;
                try {
                    const errorJson = await response.json();
                    if (errorJson && errorJson.detail) {
                        errorMessage = typeof errorJson.detail === "string" 
                            ? errorJson.detail 
                            : JSON.stringify(errorJson.detail);
                    }
                } catch (_) {
                    // Fallback to default error message if JSON parsing fails
                }
                const error = new Error(errorMessage);
                error.status = response.status;
                throw error;
            }

            // Return blob if response is a file download attachment
            const contentType = response.headers.get("Content-Type") || "";
            if (contentType.includes("application/vnd") || contentType.includes("octet-stream")) {
                return await response.blob();
            }

            // Return JSON payload
            if (contentType.includes("application/json")) {
                return await response.json();
            }

            return await response.text();
        } catch (err) {
            console.error(`[ApiClient Error] ${options.method || 'GET'} ${url}:`, err);
            throw err;
        }
    }

    get(endpoint, headers = {}) {
        return this.request(endpoint, { method: "GET", headers });
    }

    post(endpoint, body = null, headers = {}) {
        return this.request(endpoint, { method: "POST", body, headers });
    }

    put(endpoint, body = null, headers = {}) {
        return this.request(endpoint, { method: "PUT", body, headers });
    }

    delete(endpoint, headers = {}) {
        return this.request(endpoint, { method: "DELETE", headers });
    }
}

export const apiClient = new ApiClient();
export default apiClient;
