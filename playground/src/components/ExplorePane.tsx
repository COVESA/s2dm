import { DocExplorer } from "@graphiql/plugin-doc-explorer";
import { GraphiQLProvider, useGraphiQLActions } from "@graphiql/react";
import { buildSchema, execute, parse } from "graphql";
import { Download } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Pane } from "@/components/Pane";
import { QueryEditorWrapper } from "@/components/QueryEditorWrapper";
import { SchemaVisualizer } from "@/components/SchemaVisualizer";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { FormLabel } from "@/components/ui/form-label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SELECTION_QUERY_FILENAME } from "@/constants";
import { useTheme } from "@/hooks/useTheme";
import {
	selectExporterByEndpoint,
	selectSelectedExporterEndpoint,
} from "@/store/capabilities/capabilitiesSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	selectFilteredSchema,
	selectOriginalSchema,
} from "@/store/schema/schemaSlice";
import {
	pruningStart,
	resetSelectionQuery,
	selectIsPruning,
	selectSelectionQuery,
} from "@/store/selection/selectionSlice";
import {
	selectInputPaneCollapsed,
	selectResultPaneCollapsed,
	toggleInputPane,
	toggleResultPane,
} from "@/store/ui/uiSlice";
import { downloadTextFile } from "@/utils/download";
import "@graphiql/react/style.css";
import "@/components/graphiql-theme.css";

type ExplorePaneProps = {
	position?: "none" | "left" | "center" | "right";
	className?: string;
};

type ExploreTab = "graphiql" | "voyager";

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
	const selectionQuery = useAppSelector(selectSelectionQuery);
	const selectedExporterEndpoint = useAppSelector(
		selectSelectedExporterEndpoint,
	);
	const selectedExporter = useAppSelector((state) =>
		selectExporterByEndpoint(state, selectedExporterEndpoint),
	);
	const isPruning = useAppSelector(selectIsPruning);
	const inputCollapsed = useAppSelector(selectInputPaneCollapsed);
	const resultCollapsed = useAppSelector(selectResultPaneCollapsed);
	const [activeTab, setActiveTab] = useState<ExploreTab>("graphiql");
	const [selectionQueryState, setSelectionQueryState] =
		useState(selectionQuery);
	const [queryHasErrors, setQueryHasErrors] = useState(false);
	const [showExploreHelp, setShowExploreHelp] = useState(false);
	const [savedExpandedPanes, setSavedExpandedPanes] = useState({
		input: false,
		result: false,
	});
	const prevTabRef = useRef<ExploreTab>(activeTab);
	const isSelectionQueryRequired =
		selectedExporter?.requiresSelectionQuery ?? false;

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
					errors: [
						{ message: error instanceof Error ? error.message : String(error) },
					],
				};
			}
		};
	}, [graphqlSchema]);

	useEffect(() => {
		const didSwitchToVoyager =
			activeTab === "voyager" && prevTabRef.current !== "voyager";

		if (!didSwitchToVoyager) {
			return;
		}

		setSavedExpandedPanes({
			input: !inputCollapsed,
			result: !resultCollapsed,
		});

		if (!inputCollapsed) dispatch(toggleInputPane());
		if (!resultCollapsed) dispatch(toggleResultPane());
	}, [activeTab, inputCollapsed, resultCollapsed, dispatch]);

	useEffect(() => {
		const didSwitchToGraphiQL =
			activeTab === "graphiql" && prevTabRef.current !== "graphiql";
		prevTabRef.current = activeTab;

		if (!didSwitchToGraphiQL) {
			return;
		}

		if (savedExpandedPanes.input && inputCollapsed) {
			dispatch(toggleInputPane());
		}
		if (savedExpandedPanes.result && resultCollapsed) {
			dispatch(toggleResultPane());
		}
	}, [
		activeTab,
		savedExpandedPanes.input,
		savedExpandedPanes.result,
		inputCollapsed,
		resultCollapsed,
		dispatch,
	]);

	useEffect(() => {
		if (activeTab !== "graphiql") {
			return;
		}

		const applySearchPlaceholder = () => {
			const searchInputs = document.querySelectorAll<HTMLInputElement>(
				'.graphiql-doc-explorer-search input[role="combobox"]',
			);

			for (const searchInput of searchInputs) {
				if (searchInput.placeholder !== "Search") {
					searchInput.placeholder = "Search";
				}
			}
		};

		applySearchPlaceholder();
		const timer = window.setTimeout(applySearchPlaceholder, 100);
		const observerTarget =
			document.querySelector(".graphiql-container") || document.body;
		const observer = new MutationObserver(applySearchPlaceholder);
		observer.observe(observerTarget, {
			childList: true,
			subtree: true,
		});

		return () => {
			window.clearTimeout(timer);
			observer.disconnect();
		};
	}, [activeTab]);

	const handleDownloadQuery = () => {
		if (!selectionQuery) {
			return;
		}

		downloadTextFile(selectionQuery, SELECTION_QUERY_FILENAME);
	};

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
				<Tabs
					value={activeTab}
					onValueChange={(value) => setActiveTab(value as ExploreTab)}
					className="flex-1 flex flex-col"
				>
					<div className="my-2 px-4 flex items-center justify-center gap-2">
						<TabsList>
							<TabsTrigger value="graphiql">GraphiQL Explorer</TabsTrigger>
							<TabsTrigger value="voyager">Schema Visualizer</TabsTrigger>
						</TabsList>
						<Button
							variant="outline"
							size="icon-xs"
							onClick={() => setShowExploreHelp(true)}
							aria-label="Explore pane help"
							title="How this works"
						>
							?
						</Button>
					</div>

					<Dialog open={showExploreHelp} onOpenChange={setShowExploreHelp}>
						<DialogContent className="sm:max-w-2xl">
							<DialogHeader>
								<DialogTitle>Explore Pane</DialogTitle>
								<DialogDescription>
									Explore Pane helps you decide what to export.
								</DialogDescription>
							</DialogHeader>
							<ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
								<li>
									<span className="font-medium text-foreground">GraphiQL Explorer:</span>{" "}
									browse schema docs and build a Selection Query.
								</li>
								<li>
									<span className="font-medium text-foreground">Apply Selection:</span>{" "}
									filters the schema used by export commands.
								</li>
								<li>
									<span className="font-medium text-foreground">Schema Visualizer:</span>{" "}
									view the current original or filtered schema as a graph.
								</li>
								<li>
									<span className="font-medium text-foreground">Reset Selection:</span>{" "}
									restore the original unfiltered schema.
								</li>
								<li>
									<span className="font-medium text-foreground">Download Selection Query:</span>{" "}
									save the current selection query as a file.
								</li>
							</ul>
						</DialogContent>
					</Dialog>

					<TabsContent value="graphiql" className="flex-1 min-h-0 mt-0">
						<div className="h-full w-full flex flex-col relative">
							<div className="absolute top-4 right-4 z-10 flex gap-2">
								<Button
									onClick={() => dispatch(pruningStart(selectionQueryState))}
									disabled={
										selectionQueryState === selectionQuery || queryHasErrors
									}
									loading={isPruning}
								>
									Apply Selection
								</Button>
								<Button
									onClick={() => dispatch(resetSelectionQuery())}
									variant="destructive"
									disabled={!selectionQuery}
								>
									Reset Selection
								</Button>
								<Button
									onClick={handleDownloadQuery}
									variant="outline"
									size="icon"
									disabled={!selectionQuery}
									aria-label="Download Selection Query"
									title="Download Selection Query"
								>
									<Download className="h-4 w-4" />
								</Button>
							</div>
							<GraphiQLProvider
								schema={graphqlSchema}
								fetcher={fetcher}
								schemaDescription={true}
								editorTheme={{ light: "vs", dark: "vs-dark" }}
							>
								<GraphiQLThemeSync />
								<div className="graphiql-container flex-1 flex flex-row overflow-hidden">
									<div className="w-[300px] h-full min-w-[200px] max-w-[500px] border-r border-[color:var(--color-border)] overflow-hidden">
										<DocExplorer />
									</div>
									<div className="flex-1 h-full flex flex-col min-w-0 overflow-hidden">
									<div className="px-6 py-4 border-b">
										<FormLabel
											showRequired={isSelectionQueryRequired}
											className="text-2xl leading-none font-bold text-foreground"
										>
											Selection Query
										</FormLabel>
									</div>
										<QueryEditorWrapper
											selectionQuery={selectionQueryState}
											onSelectionQueryChange={setSelectionQueryState}
											onValidationChange={setQueryHasErrors}
										/>
									</div>
								</div>
							</GraphiQLProvider>
						</div>
					</TabsContent>

					<TabsContent value="voyager" className="flex-1 min-h-0 mt-0">
						<div className="h-full w-full">
							<SchemaVisualizer schema={filteredSchema} />
						</div>
					</TabsContent>
				</Tabs>
			</div>
		</Pane>
	);
}
