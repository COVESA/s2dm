import { EmptyState } from "@shared-ui/components/empty-state";
import { Tabs, TabsList, TabsTrigger } from "@shared-ui/components/tabs";
import { useEffect, useState } from "react";
import { ErrorDisplay } from "@/components/ErrorDisplay";
import { TextEditor } from "@/components/TextEditor";
import {
	FILTERED_SCHEMA_FILENAME,
	ORIGINAL_SCHEMA_FILENAME,
} from "@/constants";
import { useAppSelector } from "@/store/hooks";
import {
	selectFilteredSchema,
	selectOriginalSchema,
} from "@/store/schema/schemaSlice";
import {
	selectIsValidating,
	selectValidationErrors,
} from "@/store/validation/validationSlice";

type SchemaTab = "original" | "filtered";

type SchemaEditorProps = {
	/** The message that shows when no schema is loaded. */
	emptyMessage: string;
};

export function SchemaEditor({ emptyMessage }: SchemaEditorProps) {
	const originalSchema = useAppSelector(selectOriginalSchema);
	const filteredSchema = useAppSelector(selectFilteredSchema);
	const isValidating = useAppSelector(selectIsValidating);
	const validationErrors = useAppSelector(selectValidationErrors);
	const [activeTab, setActiveTab] = useState<SchemaTab>("original");

	const hasFilteredSchema = Boolean(
		filteredSchema?.trim() && filteredSchema !== originalSchema,
	);

	useEffect(() => {
		if (!hasFilteredSchema && activeTab === "filtered") {
			setActiveTab("original");
		}
	}, [hasFilteredSchema, activeTab]);

	if (isValidating) {
		return <EmptyState isLoading title={"Validating schema..."} />;
	}

	if (validationErrors.length > 0) {
		const errorText = validationErrors.join("\n");
		return <ErrorDisplay error={errorText} />;
	}

	if (!originalSchema?.trim()) {
		return <EmptyState title={emptyMessage} />;
	}

	let displayedSchema = originalSchema;
	let editorTitle = "Original Schema";
	let editorFileName = ORIGINAL_SCHEMA_FILENAME;
	if (activeTab === "filtered") {
		displayedSchema = filteredSchema;
		editorTitle = "Filtered Schema";
		editorFileName = FILTERED_SCHEMA_FILENAME;
	}

	return (
		<div className={"flex min-h-[40%] flex-1 flex-col"}>
			<div className={"flex justify-center mb-4"}>
				<Tabs
					value={activeTab}
					onValueChange={(value) => setActiveTab(value as SchemaTab)}
				>
					<TabsList>
						<TabsTrigger value={"original"}>Original Schema</TabsTrigger>
						<TabsTrigger value={"filtered"} disabled={!hasFilteredSchema}>
							Filtered Schema
						</TabsTrigger>
					</TabsList>
				</Tabs>
			</div>
			<div className={"flex-1 min-h-0"}>
				<TextEditor
					language={"graphql"}
					value={displayedSchema}
					readOnly
					fullscreenTitle={editorTitle}
					fileName={editorFileName}
					path={editorFileName}
				/>
			</div>
		</div>
	);
}
