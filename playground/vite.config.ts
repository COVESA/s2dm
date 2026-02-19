import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
	base: "/",
	plugins: [react(), tailwindcss()],
	worker: {
		format: "es",
	},
	resolve: {
		alias: [{ find: "@", replacement: path.resolve(__dirname, "./src") }],
		dedupe: ["monaco-editor"],
	},
	optimizeDeps: {
		include: ["react-compiler-runtime", "nullthrows"],
	},
});
