import "@graphiql/react/setup-workers/esm.sh";

import { configureLedgerWorker } from "@ledger-ui/data/ledgerClient";
import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import wasmUrl from "sql.js/dist/sql-wasm-browser.wasm?url";
import "@/index.css";
import App from "@/App.tsx";

loader.config({ monaco });
configureLedgerWorker({ wasmUrl });

const rootElement = document.getElementById("root");

if (!rootElement) {
	throw new Error("Root element not found");
}

createRoot(rootElement).render(
	<StrictMode>
		<App />
	</StrictMode>,
);
