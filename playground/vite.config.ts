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
		alias: [
			{ find: "@", replacement: path.resolve(__dirname, "./src") },
			{
				find: "@insights-ui",
				replacement: path.resolve(
					__dirname,
					"../src/s2dm/templates/insights-ui",
				),
			},
			{
				find: "@ledger-ui",
				replacement: path.resolve(__dirname, "../src/s2dm/templates/ledger-ui"),
			},
		],
		dedupe: ["monaco-editor"],
	},
	server: {
		fs: {
			allow: [path.resolve(__dirname, "..")],
		},
	},
	optimizeDeps: {
		include: ["react-compiler-runtime", "nullthrows"],
	},
});
