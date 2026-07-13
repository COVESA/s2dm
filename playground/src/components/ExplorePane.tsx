import { DocExplorer } from "@graphiql/plugin-doc-explorer";
import { GraphiQLProvider, useGraphiQLActions } from "@graphiql/react";
import { buildSchema, execute, GraphQLError, parse } from "graphql";
import { Download } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ConfirmActionDialog } from "@/components/ConfirmActionDialog";
import { HelpButton, HelpItem } from "@/components/HelpButton";
import { Pane } from "@/components/Pane";
import { QueryEditorWrapper } from "@/components/QueryEditorWrapper";
import { SchemaVisualizer } from "@/components/SchemaVisualizer";
import { Button } from "@/components/ui/button";
import { FormLabel } from "@/components/ui/form-label";
import { StatusBanner } from "@/components/ui/status-banner";
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
import { downloadTextFile } from "@/utils/download";
import { getErrorMessage } from "@/utils/getErrorMessage";
import "@graphiql/react/style.css";
import "@/components/graphiql-theme.css";

type ExplorePaneProps = {
	position?: "none" | "left" | "center" | "right";
	className?: string;
};

function GraphiQLThemeSync() {
	const { setTheme } = useGraphiQLActions();
	const theme = useTheme();

	useEffect(() => {
		setTheme(theme);
	}, [theme, setTheme]);

	return null;
}

export function ExplorePane({
	position = "center",
	className = "flex-1",
}: ExplorePaneProps) {
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
	const isSelectionQueryRequired =
		selectedExporter?.requiresSelectionQuery ?? false;
	const hasAppliedSelection = appliedSelectionQuery.trim().length > 0;
	const hasSelectionText = selectionQuery.trim().length > 0;

	const graphqlSchema = useMemo(() => {
		if (!originalSchema?.trim()) return undefined;
		try {
			return buildSchema(originalSchema);
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

	if (!originalSchema?.trim()) {
		return (
			<Pane className={className} position={position}>
				<div className="flex-1 flex items-center justify-center bg-background text-muted-foreground">
					<p>Import a schema to start</p>
				</div>
			</Pane>
		);
	}

	if (!graphqlSchema || !fetcher) {
		return (
			<Pane className={className} position={position}>
				<div className="flex-1 flex items-center justify-center bg-background text-muted-foreground">
					<p>Invalid schema format</p>
				</div>
			</Pane>
		);
	}

	return (
		<Pane className={className} position={position}>
			<div className="h-full w-full flex flex-col">
				<div className="my-2 px-4 flex items-center justify-center gap-2">
					<SchemaVisualizer schema={filteredSchema} />
					<HelpButton title="Explore Pane" ariaLabel="Explore pane help">
						<HelpItem term="GraphiQL Explorer">
							browse schema docs and build a Selection Query.
						</HelpItem>
						<HelpItem term="Apply or Unapply Selection">
							apply or remove schema filtering using the current selection text.
						</HelpItem>
						<HelpItem term="Schema Visualizer">
							view the current original or filtered schema as a graph.
						</HelpItem>
						<HelpItem term="Reset Selection">
							clear the current selection text and remove any applied filtering.
							When exploring a dependency, this also deletes its saved
							selection.
						</HelpItem>
						<HelpItem term="Download Selection Query">
							save the current selection query as a file.
						</HelpItem>
					</HelpButton>
				</div>

				<div className="flex-1 min-h-0">
					<div className="h-full w-full flex flex-col">
						<GraphiQLProvider
							schema={graphqlSchema}
							fetcher={fetcher}
							schemaDescription={true}
							editorTheme={{ light: "vs", dark: "vs-dark" }}
						>
							<GraphiQLThemeSync />
							<div className="graphiql-container flex-1 flex flex-row overflow-hidden">
								<div
									ref={setDocExplorerNode}
									className="w-[300px] h-full min-w-[200px] max-w-[500px] border-r border-[color:var(--color-border)] overflow-hidden"
								>
									<DocExplorer />
								</div>
								<div className="flex-1 h-full flex flex-col min-w-0 overflow-hidden">
									<div className="px-6 py-4 border-b">
										<div className="flex items-center justify-between gap-2">
											<FormLabel
												showRequired={isSelectionQueryRequired}
												className="text-2xl leading-none font-bold text-foreground"
											>
												Selection Query
											</FormLabel>
											<div className="flex gap-2">
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
															disabled={
																!hasSelectionText && !hasAppliedSelection
															}
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
									<QueryEditorWrapper
										selectionQuery={selectionQuery}
										onSelectionQueryChange={handleSelectionQueryChange}
										onValidationChange={setQueryHasErrors}
									/>
								</div>
							</div>
						</GraphiQLProvider>
					</div>
				</div>
			</div>
		</Pane>
	);
}
