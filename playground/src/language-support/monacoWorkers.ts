import createEditorWorker from "https://esm.sh/monaco-editor@0.52.2/esm/vs/editor/editor.worker.js?worker";
import createJsonWorker from "https://esm.sh/monaco-editor@0.52.2/esm/vs/language/json/json.worker.js?worker";
import createGraphQLWorker from "https://esm.sh/monaco-graphql@1.9.0/esm/graphql.worker.js?worker&deps=monaco-editor@0.52.2,graphql@17.0.2,graphql-language-service@5.7.0,picomatch-browser@2.2.6,nullthrows@1.1.1,vscode-languageserver-types@3.18.5";

/**
 * Lets Monaco start the editor, JSON and GraphQL workers from esm.sh, at the
 * exact package versions in the URLs.
 */
window.MonacoEnvironment = {
	getWorker(_workerId, label) {
		if (label === "json") {
			return createJsonWorker();
		}
		if (label === "graphql") {
			return createGraphQLWorker();
		}
		return createEditorWorker();
	},
};
