import {
	DocExplorer,
	type DocExplorerNavStack,
	useDocExplorer,
	useDocExplorerActions,
} from "@graphiql/plugin-doc-explorer";
import { GraphiQLProvider, useGraphiQLActions } from "@graphiql/react";
import { buildSchema, execute, GraphQLError, parse } from "graphql";
import { Columns2, Download, FileCode, type LucideIcon, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ConfirmActionDialog } from "@/components/ConfirmActionDialog";
import { SelectionTree } from "@/components/explore/SelectionTree";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

const DEFAULT_TREE_WIDTH_PERCENT = 25;
const MIN_TREE_WIDTH_PERCENT = 25;
const MAX_TREE_WIDTH_PERCENT = 70;

function clampTreeWidthPercent(percent: number): number {
	const boundedBelowPercent = Math.max(percent, MIN_TREE_WIDTH_PERCENT);
	return Math.min(boundedBelowPercent, MAX_TREE_WIDTH_PERCENT);
}

/** The root page that `reset` leaves, plus the one page the tree opens. */
const FIRST_DOCS_PAGE_STACK_LENGTH = 2;

/**
 * Tracks the tree pane's width as a share of the split row, resizable by
 * dragging the handle or with the left and right arrow keys.
 *
 * @returns The split row ref, the current width percent, and the handle's
 * event handlers.
 */
function useTreeResize() {
	const splitRowRef = useRef<HTMLDivElement>(null);
	const [treeWidthPercent, setTreeWidthPercent] = useState(
		DEFAULT_TREE_WIDTH_PERCENT,
	);

	const handlePointerDown = (event: React.PointerEvent<HTMLHRElement>) => {
		event.preventDefault();
		event.currentTarget.setPointerCapture(event.pointerId);
	};

	const handlePointerMove = (event: React.PointerEvent<HTMLHRElement>) => {
		const splitRow = splitRowRef.current;
		const isDragging = event.currentTarget.hasPointerCapture(event.pointerId);
		if (!splitRow || !isDragging) {
			return;
		}

		const splitRowBounds = splitRow.getBoundingClientRect();
		const treeWidth = event.clientX - splitRowBounds.left;
		const widthPercent = (treeWidth / splitRowBounds.width) * 100;
		const boundedPercent = clampTreeWidthPercent(widthPercent);
		setTreeWidthPercent(boundedPercent);
	};

	const handleKeyDown = (event: React.KeyboardEvent<HTMLHRElement>) => {
		let step = 0;
		if (event.key === "ArrowLeft") {
			step = -1;
		} else if (event.key === "ArrowRight") {
			step = 1;
		}
		if (step === 0) {
			return;
		}

		event.preventDefault();
		setTreeWidthPercent((currentPercent) =>
			clampTreeWidthPercent(currentPercent + step),
		);
	};

	return {
		splitRowRef,
		treeWidthPercent,
		handlePointerDown,
		handlePointerMove,
		handleKeyDown,
	};
}

const SELECTION_MODES: {
	value: SelectionMode;
	label: string;
	icon: LucideIcon;
}[] = [
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
	const [docExplorerNode, setDocExplorerNode] = useState<HTMLDivElement | null>(
		null,
	);
	const [queryHasErrors, setQueryHasErrors] = useState(false);
	const [lastValidatedQuery, setLastValidatedQuery] = useState<ValidatedQuery>({
		text: "",
		document: null,
	});
	const queryEditorRef = useRef<QueryEditorHandle>(null);
	const treeResize = useTreeResize();
	const [selectionMode, setSelectionMode] = useState<SelectionMode>("split");
	const [isDocsOpen, setIsDocsOpen] = useState(false);
	const docExplorerNavStack: DocExplorerNavStack = useDocExplorer();
	const docExplorerActions = useDocExplorerActions();
	const isBackToDocsRoot =
		docExplorerNavStack.length <= FIRST_DOCS_PAGE_STACK_LENGTH;
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

	useEffect(() => {
		if (!docExplorerNode) {
			return;
		}

		const applySearchPlaceholder = () => {
			const searchInputs = docExplorerNode.querySelectorAll<HTMLInputElement>(
				'.graphiql-doc-explorer-search input[role="combobox"]',
			);

			for (const searchInput of searchInputs) {
				if (searchInput.placeholder !== "Search") {
					searchInput.placeholder = "Search";
				}
			}
		};

		applySearchPlaceholder();
		const observer = new MutationObserver(applySearchPlaceholder);
		observer.observe(docExplorerNode, {
			childList: true,
			subtree: true,
		});

		return () => {
			observer.disconnect();
		};
	}, [docExplorerNode]);

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

	const handleSelectionModeChange = (value: string) => {
		const mode = SELECTION_MODES.find(
			(selectionModeOption) => selectionModeOption.value === value,
		);
		if (mode) {
			setSelectionMode(mode.value);
		}
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
							<hr
								className={cn(
									"m-0 h-auto w-1 shrink-0 cursor-col-resize touch-none self-stretch border-0 outline-none hover:bg-primary/30 focus-visible:bg-primary/30",
									{ hidden: isTreeHidden },
								)}
								onPointerDown={treeResize.handlePointerDown}
								onPointerMove={treeResize.handlePointerMove}
								onKeyDown={treeResize.handleKeyDown}
								tabIndex={0}
								aria-orientation={"vertical"}
								aria-valuemin={MIN_TREE_WIDTH_PERCENT}
								aria-valuemax={MAX_TREE_WIDTH_PERCENT}
								aria-valuenow={treeResize.treeWidthPercent}
								aria-label={"Resize the schema tree"}
								title={"Drag to resize"}
							/>
							<div className={"relative flex min-w-0 flex-1 flex-col"}>
								<Tabs
									value={selectionMode}
									onValueChange={handleSelectionModeChange}
									className={"absolute top-2 right-2 z-10"}
								>
									<TabsList>
										{SELECTION_MODES.map(({ value, label, icon: Icon }) => (
											<TabsTrigger
												key={value}
												value={value}
												aria-label={label}
												title={label}
											>
												<Icon className={"size-4"} />
											</TabsTrigger>
										))}
									</TabsList>
								</Tabs>
								<QueryEditorWrapper
									ref={queryEditorRef}
									selectionQuery={selectionQuery}
									onSelectionQueryChange={handleSelectionQueryChange}
									onValidated={handleQueryValidated}
								/>
							</div>
							<div
								className={cn(
									"shrink-0 overflow-hidden border-[color:var(--color-border)] transition-[width,visibility] duration-200 ease-in-out motion-reduce:transition-none",
									{
										"visible w-[300px] border-l": isDocsOpen,
										"invisible w-0": !isDocsOpen,
									},
								)}
								aria-hidden={!isDocsOpen}
							>
								<div
									ref={setDocExplorerNode}
									className={cn(
										"relative h-full w-[300px] [&_.graphiql-doc-explorer-search]:hidden!",
										{
											"[&_.graphiql-doc-explorer-back]:hidden!":
												isBackToDocsRoot,
										},
									)}
								>
									<Button
										type={"button"}
										variant={"ghost"}
										size={"icon-sm"}
										className={"absolute top-2 right-2 z-10"}
										onClick={() => setIsDocsOpen(false)}
										aria-label={"Close Docs"}
										title={"Close Docs"}
									>
										<X className={"size-4"} />
									</Button>
									<DocExplorer />
								</div>
							</div>
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
