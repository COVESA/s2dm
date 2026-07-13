import { Eye, Hammer, Layers, Package, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorDisplay } from "@/components/ErrorDisplay";
import { FileList } from "@/components/FileList";
import { HelpButton, HelpItem } from "@/components/HelpButton";
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
			<div className="absolute left-2 top-2 z-10 flex items-center gap-2">
				<ThemeToggle />
				<HelpButton
					title="Schema Files & Dependencies"
					ariaLabel="Schema files help"
				>
					<HelpItem
						term={
							<>
								<Package className="inline h-4 w-4 align-text-bottom" /> Manage
								dependencies
							</>
						}
					>
						open the dependency manager to configure, resolve, and build
						external schema dependencies. Disabled while exploring a dependency.
					</HelpItem>
					<HelpItem
						term={
							<>
								<Plus className="inline h-4 w-4 align-text-bottom" /> Add
								schemas
							</>
						}
					>
						import schema files, a whole directory, or add a schema from a URL.
					</HelpItem>
					<HelpItem
						term={
							<>
								<Trash2 className="inline h-4 w-4 align-text-bottom" /> Remove
								all files
							</>
						}
					>
						clear every imported source file from the list.
					</HelpItem>
					<HelpItem term="Dependencies section">
						lists the resolved dependencies. Use{" "}
						<Hammer className="inline h-4 w-4 align-text-bottom" /> Build to
						compose them into a single schema (the dropdown offers Build and
						Auto-prefix), and{" "}
						<Eye className="inline h-4 w-4 align-text-bottom" /> to preview that
						built dependency schema.
					</HelpItem>
					<HelpItem term="Files section">
						lists the imported source files. Drag entries to reorder them.
					</HelpItem>
					<HelpItem
						term={
							<>
								<Layers className="inline h-4 w-4 align-text-bottom" /> Compose
								and Validate
							</>
						}
					>
						validate and compose all source files into one schema. Tick “Include
						built dependencies in composition” to merge the built dependency
						schema into the result.
					</HelpItem>
				</HelpButton>
			</div>

			<FileList />

			{originalSchema?.trim() && <Separator />}

			{renderSchemaEditor()}
		</Pane>
	);
}
