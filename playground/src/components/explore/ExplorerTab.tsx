import { useDocExplorerActions } from "@graphiql/plugin-doc-explorer";
import { GraphiQLProvider, useGraphiQLActions } from "@graphiql/react";
import { buildSchema, execute, GraphQLError, parse } from "graphql";
import { Columns2, Download, FileCode } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ConfirmActionDialog } from "@/components/ConfirmActionDialog";
import { DocsPanel } from "@/components/explore/DocsPanel";
import { type IconTabOption, IconTabs } from "@/components/explore/IconTabs";
import { SelectionTree } from "@/components/explore/SelectionTree";
import {
	TreeResizeHandle,
	useTreeResize,
} from "@/components/explore/TreeResizeHandle";
import { HelpButton, HelpItem } from "@/components/HelpButton";
import {
	type QueryEditorHandle,
	QueryEditorWrapper,
	type ValidatedQuery,
} from "@/components/QueryEditorWrapper";
import { SchemaVisualizer } from "@/components/SchemaVisualizer";
import { Button } from "@/components/ui/button";
import { FormLabel } from "@/components/ui/form-label";
import { StatusBanner } from "@/components/ui/status-banner";
import { TabsContent } from "@/components/ui/tabs";
import { SELECTION_QUERY_FILENAME } from "@/constants";
import { useTheme } from "@/hooks/useTheme";
import {
	selectExporterByEndpoint,
	selectSelectedExporterEndpoint,
} from "@/store/capabilities/capabilitiesSlice";
import { selectExploringDependencyId } from "@/store/deps/dependencyExploration/dependencyExplorationSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	selectFilteredSchema,
	selectOriginalSchema,
} from "@/store/schema/schemaSlice";
import {
	clearAppliedSelection,
	pruningStart,
	resetSelection,
	selectAppliedSelectionQuery,
	selectIsPruning,
	selectPruningError,
	selectSelectionQuery,
	setSelectionQuery,
} from "@/store/selection/selectionSlice";
import { cn } from "@/utils/cn";
import { downloadTextFile } from "@/utils/download";
import { getErrorMessage } from "@/utils/getErrorMessage";
import { withPickDirective } from "@/utils/selectionQuery/pick";
import "@graphiql/react/style.css";
import "@/components/graphiql-theme.css";

type SelectionMode = "text" | "split";

const SELECTION_MODES: IconTabOption<SelectionMode>[] = [
	{ value: "split", label: "Split", icon: Columns2 },
	{ value: "text", label: "Text", icon: FileCode },
];

function GraphiQLThemeSync() {
	const { setTheme } = useGraphiQLActions();
	const theme = useTheme();

	useEffect(() => {
		setTheme(theme);
	}, [theme, setTheme]);

	return null;
}

export function ExplorerTab() {
	const dispatch = useAppDispatch();
	const originalSchema = useAppSelector(selectOriginalSchema);
	const filteredSchema = useAppSelector(selectFilteredSchema);
	const appliedSelectionQuery = useAppSelector(selectAppliedSelectionQuery);
	const selectionQuery = useAppSelector(selectSelectionQuery);
	const exploringDependencyId = useAppSelector(selectExploringDependencyId);
	const selectedExporterEndpoint = useAppSelector(
		selectSelectedExporterEndpoint,
	);
	const selectedExporter = useAppSelector((state) =>
		selectExporterByEndpoint(state, selectedExporterEndpoint),
	);
	const isPruning = useAppSelector(selectIsPruning);
	const pruningError = useAppSelector(selectPruningError);
	const [queryHasErrors, setQueryHasErrors] = useState(false);
	const [lastValidatedQuery, setLastValidatedQuery] = useState<ValidatedQuery>({
		text: "",
		document: null,
	});
	const queryEditorRef = useRef<QueryEditorHandle>(null);
	const treeResize = useTreeResize();
	const [selectionMode, setSelectionMode] = useState<SelectionMode>("split");
	const [isDocsOpen, setIsDocsOpen] = useState(false);
	const docExplorerActions = useDocExplorerActions();
	const isSelectionQueryRequired =
		selectedExporter?.requiresSelectionQuery ?? false;
	const hasAppliedSelection = appliedSelectionQuery.trim().length > 0;
	const hasSelectionText = selectionQuery.trim().length > 0;

	const graphqlSchema = useMemo(() => {
		if (!originalSchema?.trim()) return undefined;
		try {
			const builtSchema = buildSchema(originalSchema);
			return withPickDirective(builtSchema);
		} catch {
			return undefined;
		}
	}, [originalSchema]);

	const fetcher = useMemo(() => {
		if (!graphqlSchema) return undefined;

		return async (graphQLParams: {
			query?: string;
			variables?: Record<string, unknown>;
			operationName?: string | null;
		}) => {
			if (!graphQLParams.query) {
				return { data: null };
			}

			try {
				const document = parse(graphQLParams.query);
				const result = await execute({
					schema: graphqlSchema,
					document,
					variableValues: graphQLParams.variables,
					operationName: graphQLParams.operationName,
				});
				return result;
			} catch (error) {
				console.error("Fetcher error:", error);
				return {
					errors: [new GraphQLError(getErrorMessage(error))],
				};
			}
		};
	}, [graphqlSchema]);

	const handleDownloadQuery = () => {
		if (!selectionQuery) {
			return;
		}

		downloadTextFile(selectionQuery, SELECTION_QUERY_FILENAME);
	};

	const handleSelectionQueryChange = useCallback(
		(value: string) => {
			dispatch(setSelectionQuery(value));
		},
		[dispatch],
	);

	const handleQueryValidated = useCallback(
		(validatedQuery: ValidatedQuery | null) => {
			setQueryHasErrors(validatedQuery === null);
			if (validatedQuery) {
				setLastValidatedQuery(validatedQuery);
			}
		},
		[],
	);

	const handleOpenDocs = () => {
		docExplorerActions.reset();
		setIsDocsOpen(true);
	};

	const handleTreeEdit = (text: string) => {
		queryEditorRef.current?.replaceQuery(text);
	};

	const handleSelectionAction = () => {
		if (hasAppliedSelection) {
			dispatch(clearAppliedSelection());
			return;
		}

		dispatch(pruningStart(selectionQuery));
	};

	let selectionActionLabel = "Apply Selection";
	if (hasAppliedSelection) {
		selectionActionLabel = "Unapply Selection";
	}

	let resetDescription =
		"This will clear the selection text and remove the applied filtering.";
	if (exploringDependencyId) {
		resetDescription =
			"This will clear the selection text, remove the applied filtering, and delete the saved selection for the explored dependency.";
	}

	let isSelectionActionDisabled = false;
	if (!hasAppliedSelection) {
		isSelectionActionDisabled = !hasSelectionText || queryHasErrors;
	}

	const isTreeHidden = selectionMode === "text";

	let content: React.ReactNode;
	if (!graphqlSchema || !fetcher) {
		content = (
			<div className="flex-1 flex items-center justify-center bg-background text-muted-foreground">
				<p>Invalid schema format</p>
			</div>
		);
	} else {
		content = (
			<GraphiQLProvider
				schema={graphqlSchema}
				fetcher={fetcher}
				schemaDescription={true}
				editorTheme={{ light: "vs", dark: "vs-dark" }}
			>
				<GraphiQLThemeSync />
				<div className="graphiql-container flex-1 flex flex-row overflow-hidden">
					<div className="flex-1 h-full flex flex-col min-w-0 overflow-hidden">
						<div className="px-6 py-4 border-b">
							<div className="flex items-center justify-between gap-2">
								<FormLabel
									showRequired={isSelectionQueryRequired}
									className="text-2xl leading-none font-bold text-foreground"
								>
									Selection Query
								</FormLabel>
								<div className="flex items-center gap-2">
									<HelpButton title="Explorer" ariaLabel="Explorer help">
										<HelpItem term="Split or Text">
											build the Selection Query by checking fields in a tree
											beside the editor, or write it as text only.
										</HelpItem>
										<HelpItem term="Apply or Unapply Selection">
											apply or remove schema filtering using the current
											selection text.
										</HelpItem>
										<HelpItem term="Schema Visualizer">
											view the current original or filtered schema as a graph.
										</HelpItem>
										<HelpItem term="Reset Selection">
											clear the current selection text and remove any applied
											filtering. When exploring a dependency, this also deletes
											its saved selection.
										</HelpItem>
										<HelpItem term="Download Selection Query">
											save the current selection query as a file.
										</HelpItem>
									</HelpButton>
									<SchemaVisualizer schema={filteredSchema} />
									<Button
										onClick={handleSelectionAction}
										disabled={isSelectionActionDisabled}
										loading={isPruning && !hasAppliedSelection}
									>
										{selectionActionLabel}
									</Button>
									<ConfirmActionDialog
										trigger={
											<Button
												variant="destructive"
												disabled={!hasSelectionText && !hasAppliedSelection}
											>
												Reset Selection
											</Button>
										}
										title="Reset selection?"
										description={resetDescription}
										confirmLabel="Reset Selection"
										onConfirm={() => dispatch(resetSelection())}
									/>
									<Button
										onClick={handleDownloadQuery}
										variant="outline"
										size="icon"
										disabled={!hasSelectionText}
										aria-label="Download Selection Query"
										title="Download Selection Query"
									>
										<Download className="h-4 w-4" />
									</Button>
								</div>
							</div>
							{pruningError && (
								<StatusBanner
									variant="destructive"
									className="mt-4 whitespace-pre-wrap"
								>
									{pruningError}
								</StatusBanner>
							)}
						</div>
						<div
							ref={treeResize.splitRowRef}
							className={"flex min-h-0 flex-1 flex-row"}
						>
							<div
								className={cn("flex min-w-0 shrink-0 flex-col border-r", {
									hidden: isTreeHidden,
								})}
								style={{ width: `${treeResize.treeWidthPercent}%` }}
							>
								<SelectionTree
									selectionQuery={selectionQuery}
									validatedQuery={lastValidatedQuery}
									hasQueryErrors={queryHasErrors}
									onTreeEdit={handleTreeEdit}
									onOpenDocs={handleOpenDocs}
								/>
							</div>
							<TreeResizeHandle
								treeResize={treeResize}
								isHidden={isTreeHidden}
							/>
							<div className={"relative flex min-w-0 flex-1 flex-col"}>
								<IconTabs
									options={SELECTION_MODES}
									value={selectionMode}
									onValueChange={setSelectionMode}
									className={"absolute top-2 right-2 z-10"}
								/>
								<QueryEditorWrapper
									ref={queryEditorRef}
									selectionQuery={selectionQuery}
									onSelectionQueryChange={handleSelectionQueryChange}
									onValidated={handleQueryValidated}
								/>
							</div>
							<DocsPanel
								isOpen={isDocsOpen}
								onClose={() => setIsDocsOpen(false)}
							/>
						</div>
					</div>
				</div>
			</GraphiQLProvider>
		);
	}

	return (
		<TabsContent value="explorer" className="mt-0 flex min-h-0 flex-1 flex-col">
			{content}
		</TabsContent>
	);
}
