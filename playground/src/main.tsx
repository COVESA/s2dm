import "@graphiql/react/setup-workers/esm.sh";

import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@/index.css";
import App from "@/App.tsx";

loader.config({ monaco });

const rootElement = document.getElementById("root");

if (!rootElement) {
	throw new Error("Root element not found");
}

createRoot(rootElement).render(
	<StrictMode>
		<App />
	</StrictMode>,
);
