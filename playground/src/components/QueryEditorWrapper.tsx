import { QueryEditor, useEditorContext, useGraphiQL } from "@graphiql/react";
import { type DocumentNode, parse, validate } from "graphql";
import {
	forwardRef,
	type MutableRefObject,
	useEffect,
	useImperativeHandle,
	useRef,
} from "react";

/**
 * A selection query that passed validation.
 *
 * `text` is the text that was validated. `document` is its parsed form, or
 * `null` when the text is empty, which counts as valid.
 */
export type ValidatedQuery = {
	text: string;
	document: DocumentNode | null;
};

export type QueryEditorHandle = {
	replaceQuery: (text: string) => void;
};

type QueryEditorWrapperProps = {
	selectionQuery: string;
	onSelectionQueryChange: (value: string) => void;
	/** Called after each validation; `null` when the query doesn't parse or validate. */
	onValidated?: (validatedQuery: ValidatedQuery | null) => void;
};

const TYPING_VALIDATION_DELAY_MS = 500;

/**
 * Applies an editor change that does not come from typing, with the flag set
 * for its duration so the change listener skips the typing debounce. The flag
 * is reset even when the change throws.
 *
 * @param isProgrammaticChangeRef The flag the change listener reads; mutated.
 * @param applyChange The editor change to apply.
 */
function runProgrammaticChange(
	isProgrammaticChangeRef: MutableRefObject<boolean>,
	applyChange: () => void,
) {
	isProgrammaticChangeRef.current = true;
	try {
		applyChange();
	} finally {
		isProgrammaticChangeRef.current = false;
	}
}

export const QueryEditorWrapper = forwardRef<
	QueryEditorHandle,
	QueryEditorWrapperProps
>(function QueryEditorWrapper(
	{ selectionQuery, onSelectionQueryChange, onValidated },
	ref,
) {
	const { queryEditor } = useEditorContext();
	const schema = useGraphiQL((state) => state.schema);
	const validationTimeoutRef = useRef<number | null>(null);
	const isProgrammaticChangeRef = useRef(false);

	useImperativeHandle(
		ref,
		() => ({
			replaceQuery: (text: string) => {
				const model = queryEditor?.getModel();
				if (!queryEditor || !model) {
					return;
				}

				const fullRange = model.getFullModelRange();
				runProgrammaticChange(isProgrammaticChangeRef, () => {
					queryEditor.executeEdits("selection-tree", [
						{ range: fullRange, text },
					]);
					queryEditor.pushUndoStop();
				});
			},
		}),
		[queryEditor],
	);

	useEffect(() => {
		if (!queryEditor) return;

		queryEditor.updateOptions({ contextmenu: false });

		if (selectionQuery !== queryEditor.getValue()) {
			runProgrammaticChange(isProgrammaticChangeRef, () =>
				queryEditor.setValue(selectionQuery),
			);
		}
	}, [queryEditor, selectionQuery]);

	useEffect(() => {
		if (!queryEditor) return;

		const validateQuery = (query: string) => {
			if (!onValidated) {
				return;
			}

			if (!query.trim()) {
				onValidated({ text: query, document: null });
				return;
			}

			let document: DocumentNode;
			try {
				document = parse(query);
			} catch {
				onValidated(null);
				return;
			}

			if (schema) {
				const errors = validate(schema, document);
				if (errors.length > 0) {
					onValidated(null);
					return;
				}
			}

			onValidated({ text: query, document });
		};

		const disposable = queryEditor.onDidChangeModelContent(() => {
			const value = queryEditor.getValue();
			onSelectionQueryChange(value);

			if (validationTimeoutRef.current !== null) {
				clearTimeout(validationTimeoutRef.current);
			}

			if (isProgrammaticChangeRef.current) {
				validateQuery(value);
				return;
			}

			validationTimeoutRef.current = setTimeout(() => {
				validateQuery(value);
			}, TYPING_VALIDATION_DELAY_MS);
		});

		const currentValue = queryEditor.getValue();
		validateQuery(currentValue);

		return () => {
			disposable.dispose();
			if (validationTimeoutRef.current !== null) {
				clearTimeout(validationTimeoutRef.current);
			}
		};
	}, [queryEditor, onSelectionQueryChange, onValidated, schema]);

	return (
		<div className="relative flex-1 min-h-0 overflow-hidden">
			<QueryEditor />
		</div>
	);
});
