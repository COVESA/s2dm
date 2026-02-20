import { useCallback, useEffect, useState } from "react";
import { ErrorDisplay } from "@/components/ErrorDisplay";
import { FileList } from "@/components/FileList";
import { Pane } from "@/components/Pane";
import { TextEditor } from "@/components/TextEditor";
import { ThemeToggle } from "@/components/ThemeToggle";
import { EmptyState } from "@/components/ui/empty-state";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
	FILTERED_SCHEMA_FILENAME,
	ORIGINAL_SCHEMA_FILENAME,
} from "@/constants";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	selectFilteredSchema,
	selectOriginalSchema,
	selectSourceFiles,
} from "@/store/schema/schemaSlice";
import { selectInputPaneCollapsed, toggleInputPane } from "@/store/ui/uiSlice";
import {
	selectIsValidating,
	selectValidationErrors,
	validateAndCompose,
} from "@/store/validation/validationSlice";

type SchemaTab = "original" | "filtered";

type InputPaneProps = {
	position?: "none" | "left" | "center" | "right";
	collapsible?: boolean;
	className?: string;
};

export function InputPane({
	position,
	collapsible,
	className = "bg-card",
}: InputPaneProps) {
	const dispatch = useAppDispatch();
	const originalSchema = useAppSelector(selectOriginalSchema);
	const filteredSchema = useAppSelector(selectFilteredSchema);
	const isValidating = useAppSelector(selectIsValidating);
	const validationErrors = useAppSelector(selectValidationErrors);
	const isCollapsed = useAppSelector(selectInputPaneCollapsed);
	const files = useAppSelector(selectSourceFiles);
	const [activeTab, setActiveTab] = useState<SchemaTab>("original");

	const handleCompose = useCallback(() => {
		dispatch(validateAndCompose(files));
	}, [files, dispatch]);

	useEffect(() => {
		const hasFilteredSchema =
			filteredSchema?.trim() && filteredSchema !== originalSchema;
		if (!hasFilteredSchema && activeTab === "filtered") {
			setActiveTab("original");
		}
	}, [filteredSchema, originalSchema, activeTab]);

	const renderSchemaEditor = () => {
		if (isValidating) {
			return <EmptyState isLoading title="Validating schema..." />;
		}

		if (validationErrors.length > 0) {
			return <ErrorDisplay error={validationErrors.join("\n")} />;
		}

		if (!originalSchema?.trim()) {
			let message = "Nothing to display";
			if (files.length === 1) {
				message = 'Nothing to display. Click "Validate" to start.';
			} else if (files.length > 1) {
				message = 'Nothing to display. Click "Compose and Validate" to start.';
			}
			return <EmptyState title={message} />;
		}

		const hasFilteredSchema =
			filteredSchema?.trim() && filteredSchema !== originalSchema;
		const displayedSchema =
			activeTab === "filtered" ? filteredSchema : originalSchema;

		return (
			<div className="flex-1 min-h-0 flex flex-col">
				<div className="flex justify-center mb-4">
					<Tabs
						value={activeTab}
						onValueChange={(value) => setActiveTab(value as SchemaTab)}
					>
						<TabsList>
							<TabsTrigger value="original">Original Schema</TabsTrigger>
							<TabsTrigger value="filtered" disabled={!hasFilteredSchema}>
								Filtered Schema
							</TabsTrigger>
						</TabsList>
					</Tabs>
				</div>
				<div className="flex-1 min-h-0">
					<TextEditor
						language="graphql"
						value={displayedSchema}
						readOnly
						fullscreenTitle={
							activeTab === "filtered" ? "Filtered Schema" : "Original Schema"
						}
						fileName={
							activeTab === "filtered"
								? FILTERED_SCHEMA_FILENAME
								: ORIGINAL_SCHEMA_FILENAME
						}
					/>
				</div>
			</div>
		);
	};

	return (
		<Pane
			className={className}
			position={position}
			collapsible={collapsible}
			isCollapsed={isCollapsed}
			onToggleCollapse={() => dispatch(toggleInputPane())}
		>
			<div className="absolute left-2 top-2 z-10">
				<ThemeToggle />
			</div>

			<FileList onCompose={handleCompose} />

			{originalSchema?.trim() && <Separator />}

			{renderSchemaEditor()}
		</Pane>
	);
}
