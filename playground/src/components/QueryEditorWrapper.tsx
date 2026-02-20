import { QueryEditor, useEditorContext, useGraphiQL } from "@graphiql/react";
import { parse, validate } from "graphql";
import { useEffect, useRef } from "react";

type QueryEditorWrapperProps = {
	selectionQuery: string;
	onSelectionQueryChange: (value: string) => void;
	onValidationChange?: (hasErrors: boolean) => void;
};

export function QueryEditorWrapper({
	selectionQuery,
	onSelectionQueryChange,
	onValidationChange,
}: QueryEditorWrapperProps) {
	const { queryEditor } = useEditorContext();
	const schema = useGraphiQL((state) => state.schema);
	const validationTimeoutRef = useRef<number | null>(null);

	useEffect(() => {
		if (!queryEditor) return;

		queryEditor.updateOptions({ contextmenu: false });

		if (selectionQuery !== queryEditor.getValue()) {
			queryEditor.setValue(selectionQuery);
		}
	}, [queryEditor, selectionQuery]);

	useEffect(() => {
		if (!queryEditor || !onValidationChange) return;

		const validateQuery = (query: string) => {
			if (!query.trim()) {
				onValidationChange(false);
				return;
			}

			try {
				const document = parse(query);
				if (schema) {
					const errors = validate(schema, document);
					onValidationChange(errors.length > 0);
				} else {
					onValidationChange(false);
				}
			} catch {
				onValidationChange(true);
			}
		};

		const disposable = queryEditor.onDidChangeModelContent(() => {
			const value = queryEditor.getValue();
			onSelectionQueryChange(value);

			if (validationTimeoutRef.current !== null) {
				clearTimeout(validationTimeoutRef.current);
			}

			validationTimeoutRef.current = setTimeout(() => {
				validateQuery(value);
			}, 500);
		});

		validateQuery(queryEditor.getValue());

		return () => {
			disposable.dispose();
			if (validationTimeoutRef.current !== null) {
				clearTimeout(validationTimeoutRef.current);
			}
		};
	}, [queryEditor, onSelectionQueryChange, onValidationChange, schema]);

	return <QueryEditor />;
}
