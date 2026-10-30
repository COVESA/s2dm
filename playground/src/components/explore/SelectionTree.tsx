import {
	type DocExplorerNavStackItem,
	useDocExplorerActions,
} from "@graphiql/plugin-doc-explorer";
import { useGraphiQL } from "@graphiql/react";
import { SearchBar, type SearchMode } from "@search-ui/components/SearchBar";
import { SEMANTIC_SEARCH_LIMIT } from "@search-ui/constants";
import {
	matchesSearchTerm,
	normalizeSearchTerm,
} from "@search-ui/utils/textSearch";
import { StatusBanner } from "@shared-ui/components/status-banner";
import {
	type GraphQLObjectType,
	type GraphQLSchema,
	isInterfaceType,
	isObjectType,
} from "graphql";
import {
	type ChangeEvent,
	type ReactNode,
	useDeferredValue,
	useMemo,
	useRef,
	useState,
} from "react";
import { PickGroupItem } from "@/components/explore/PickGroupItem";
import { PickNameItem } from "@/components/explore/PickNameItem";
import { RecursionDepthStepper } from "@/components/explore/RecursionDepthStepper";
import { SelectionTreeItem } from "@/components/explore/SelectionTreeItem";
import { TreeRowList } from "@/components/explore/TreeRowList";
import { TreeExpandSpacer } from "@/components/explore/TreeRowParts";
import { HelpButton, HelpItem } from "@/components/HelpButton";
import type { ValidatedQuery } from "@/components/QueryEditorWrapper";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/ui/empty-state";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	clearSemanticSearch,
	selectEmbeddingsError,
	selectEmbeddingsStatus,
	selectMatchedElementIds,
	selectSemanticSearchError,
	semanticQueryChanged,
} from "@/store/semanticSearch/semanticSearchSlice";
import { formatSelection } from "@/utils/selectionQuery/formatSelection";
import {
	countPickSelection,
	createLeafCounter,
	getCheckedState,
} from "@/utils/selectionQuery/leafCounts";
import { patchAll } from "@/utils/selectionQuery/patchAll";
import { patchPick } from "@/utils/selectionQuery/patchPick";
import { patchSelection } from "@/utils/selectionQuery/patchSelection";
import {
	getPickableNames,
	PICK_ARGUMENT_NAMES,
	type PickArgumentName,
} from "@/utils/selectionQuery/pick";
import type { SelectionIndex } from "@/utils/selectionQuery/readSelection";
import {
	createRootNode,
	type SchemaTreeNode,
} from "@/utils/selectionQuery/schemaTree";
import {
	groupElementIds,
	listSearchableNodes,
	searchTree,
	searchTreeByElements,
} from "@/utils/selectionQuery/searchTree";
import { buildTreeRows } from "@/utils/selectionQuery/treeRows";

const PICK_GROUP_LABELS: Record<PickArgumentName, string> = {
	enums: "Enums",
	scalars: "Scalars",
	directives: "Directives",
};

const PICK_GROUPS = PICK_ARGUMENT_NAMES.map((argumentName) => ({
	argumentName,
	label: PICK_GROUP_LABELS[argumentName],
}));

type SelectionTreeProps = {
	selectionQuery: string;
	validatedQuery: ValidatedQuery;
	selection: SelectionIndex;
	hasQueryErrors: boolean;
	maxRecursionDepth: number;
	onTreeEdit: (text: string) => void;
	onOpenDocs: () => void;
	onRecursionDepthChange: (maxRecursionDepth: number) => void;
};

export function SelectionTree(props: SelectionTreeProps) {
	const schema = useGraphiQL((state) => state.schema);
	const queryType = schema?.getQueryType();
	if (!schema || !queryType) {
		return <EmptyState title={"The schema has no Query type"} />;
	}

	return (
		<SelectionTreeContent {...props} schema={schema} queryType={queryType} />
	);
}

type SelectionTreeContentProps = SelectionTreeProps & {
	schema: GraphQLSchema;
	queryType: GraphQLObjectType;
};

function SelectionTreeContent({
	selectionQuery,
	validatedQuery,
	selection,
	hasQueryErrors,
	maxRecursionDepth,
	onTreeEdit,
	onOpenDocs,
	onRecursionDepthChange,
	schema,
	queryType,
}: SelectionTreeContentProps) {
	const [isUpdating, setIsUpdating] = useState(false);
	const [expandedKeys, setExpandedKeys] = useState<Set<string>>(
		() => new Set(),
	);
	const [searchTerm, setSearchTerm] = useState("");
	const [searchMode, setSearchMode] = useState<SearchMode>("text");
	const scrollContainerRef = useRef<HTMLDivElement>(null);
	const docExplorerActions = useDocExplorerActions();
	const dispatch = useAppDispatch();
	const embeddingsStatus = useAppSelector(selectEmbeddingsStatus);
	const embeddingsError = useAppSelector(selectEmbeddingsError);
	const matchedElementIds = useAppSelector(selectMatchedElementIds);
	const semanticSearchError = useAppSelector(selectSemanticSearchError);

	const countLeaves = useMemo(() => createLeafCounter(selection), [selection]);
	const rootNode = useMemo(() => createRootNode(queryType), [queryType]);

	const deferredSearchTerm = useDeferredValue(searchTerm);
	const normalizedSearchTerm = normalizeSearchTerm(deferredSearchTerm);
	const isSemanticMode = searchMode === "semantic";
	let isSearching = normalizedSearchTerm.length > 0;
	if (isSemanticMode) {
		isSearching = matchedElementIds !== null;
	}
	const elementMatches = useMemo(() => {
		if (!isSemanticMode || matchedElementIds === null) {
			return null;
		}
		return groupElementIds(matchedElementIds, schema);
	}, [isSemanticMode, matchedElementIds, schema]);
	const searchableNodes = useMemo(() => {
		if (!isSearching) {
			return [];
		}
		return listSearchableNodes(rootNode);
	}, [rootNode, isSearching]);
	const search = useMemo(() => {
		if (!isSearching) {
			return null;
		}
		if (elementMatches) {
			return searchTreeByElements(searchableNodes, elementMatches);
		}
		return searchTree(searchableNodes, normalizedSearchTerm);
	}, [searchableNodes, normalizedSearchTerm, isSearching, elementMatches]);

	const pickGroupNames = useMemo(
		() =>
			PICK_GROUPS.map((pickGroup) => {
				const names = getPickableNames(schema, pickGroup.argumentName);
				return { ...pickGroup, names };
			}),
		[schema],
	);
	const pickGroups = useMemo(
		() =>
			pickGroupNames.map((pickGroup) => {
				let matchingNames: Set<string> | null = null;
				if (elementMatches) {
					const matchingNameList = pickGroup.names.filter((name) =>
						elementMatches.typeNames.has(name),
					);
					matchingNames = new Set(matchingNameList);
				} else if (isSearching) {
					const matchingNameList = pickGroup.names.filter((name) =>
						matchesSearchTerm(name, normalizedSearchTerm),
					);
					matchingNames = new Set(matchingNameList);
				}
				return { ...pickGroup, matchingNames };
			}),
		[pickGroupNames, isSearching, normalizedSearchTerm, elementMatches],
	);

	const rows = useMemo(
		() =>
			buildTreeRows(
				rootNode,
				pickGroups,
				expandedKeys,
				search,
				maxRecursionDepth,
			),
		[rootNode, pickGroups, expandedKeys, search, maxRecursionDepth],
	);

	const isValidationPending = validatedQuery.text !== selectionQuery;
	const isTreeDisabled = hasQueryErrors || isValidationPending || isUpdating;
	const hasNoMatches = search !== null && rows.length === 0;

	const rootLeafCounts = countLeaves(rootNode, maxRecursionDepth);
	const { pickedNamesByArgument, counts: allCounts } = countPickSelection(
		selection,
		pickGroups,
		rootLeafCounts,
	);
	const allCheckedState = getCheckedState(
		allCounts.selectedCount,
		allCounts.totalCount,
	);

	const applyTreeEdit = async (buildPatchedQuery: () => string) => {
		if (isTreeDisabled) {
			return;
		}

		setIsUpdating(true);
		try {
			const patchedQuery = buildPatchedQuery();
			const formattedQuery = await formatSelection(patchedQuery);
			onTreeEdit(formattedQuery);
		} finally {
			setIsUpdating(false);
		}
	};

	const handleToggle = (node: SchemaTreeNode, isChecked: boolean) =>
		applyTreeEdit(() =>
			patchSelection(
				validatedQuery.text,
				selection,
				node,
				isChecked,
				node.recursionDepth,
			),
		);

	const handlePickToggle = (
		argumentName: PickArgumentName,
		pickableNames: string[],
		toggledNames: string[],
		isChecked: boolean,
	) =>
		applyTreeEdit(() =>
			patchPick(
				validatedQuery.text,
				selection,
				argumentName,
				pickableNames,
				toggledNames,
				isChecked,
			),
		);

	const handleToggleAll = () =>
		applyTreeEdit(() =>
			patchAll(
				validatedQuery.text,
				rootNode,
				pickGroups,
				allCheckedState !== true,
				maxRecursionDepth,
			),
		);

	const handleToggleExpanded = (key: string) => {
		setExpandedKeys((currentKeys) => {
			const nextKeys = new Set(currentKeys);
			if (nextKeys.has(key)) {
				nextKeys.delete(key);
			} else {
				nextKeys.add(key);
			}
			return nextKeys;
		});
	};

	const handleSearchChange = (event: ChangeEvent<HTMLInputElement>) => {
		const nextSearchTerm = event.target.value;
		setSearchTerm(nextSearchTerm);
		if (isSemanticMode) {
			dispatch(semanticQueryChanged(nextSearchTerm));
		}
	};

	const handleSearchModeChange = (nextSearchMode: SearchMode) => {
		setSearchMode(nextSearchMode);
		if (nextSearchMode === "semantic") {
			dispatch(semanticQueryChanged(searchTerm));
			return;
		}
		dispatch(clearSemanticSearch());
	};

	const showInDocs = (navItem: DocExplorerNavStackItem) => {
		onOpenDocs();
		docExplorerActions.push(navItem);
	};

	const handleShowTypeDocs = (typeName: string) => {
		const type = schema.getType(typeName);
		if (!type) {
			return;
		}

		showInDocs({ name: type.name, def: type });
	};

	const handleShowDocs = (node: SchemaTreeNode) => {
		const parentType = node.parent?.type;
		if (
			node.segment?.kind === "field" &&
			(isObjectType(parentType) || isInterfaceType(parentType))
		) {
			const parentFields = parentType.getFields();
			const field = parentFields[node.segment.name];
			showInDocs({ name: field.name, def: field });
			return;
		}

		showInDocs({ name: node.type.name, def: node.type });
	};

	const renderRow = (rowIndex: number) => {
		const row = rows[rowIndex];
		if (row.kind === "field") {
			return (
				<SelectionTreeItem
					row={row}
					countLeaves={countLeaves}
					isDisabled={isTreeDisabled}
					onToggle={handleToggle}
					onToggleExpanded={handleToggleExpanded}
					onShowDocs={handleShowDocs}
				/>
			);
		}

		const pickGroup = pickGroups.find(
			({ argumentName }) => argumentName === row.argumentName,
		);
		const pickedNames = pickedNamesByArgument.get(row.argumentName);
		if (!pickGroup || !pickedNames) {
			return null;
		}

		const handleGroupToggle = (toggledNames: string[], isChecked: boolean) =>
			handlePickToggle(
				row.argumentName,
				pickGroup.names,
				toggledNames,
				isChecked,
			);

		if (row.kind === "pickGroup") {
			return (
				<PickGroupItem
					row={row}
					label={pickGroup.label}
					names={pickGroup.names}
					pickedNames={pickedNames}
					isDisabled={isTreeDisabled}
					onToggle={handleGroupToggle}
					onToggleExpanded={handleToggleExpanded}
				/>
			);
		}

		let handleShowNameDocs: ((name: string) => void) | undefined;
		if (row.argumentName !== "directives") {
			handleShowNameDocs = handleShowTypeDocs;
		}
		const isPicked = pickedNames.has(row.name);
		return (
			<PickNameItem
				row={row}
				isPicked={isPicked}
				isDisabled={isTreeDisabled}
				onToggle={handleGroupToggle}
				onShowDocs={handleShowNameDocs}
			/>
		);
	};

	const semanticSearchUnavailableMessage = `Semantic search is unavailable: ${embeddingsError}`;
	let semanticModeHint: string | undefined;
	if (embeddingsStatus === "preparing") {
		semanticModeHint = "Preparing semantic search…";
	} else if (embeddingsStatus === "failed") {
		semanticModeHint = semanticSearchUnavailableMessage;
	}

	let treeContent: ReactNode = <EmptyState title={"No matches"} />;
	if (!hasNoMatches) {
		treeContent = (
			<TreeRowList
				rows={rows}
				scrollContainerRef={scrollContainerRef}
				renderRow={renderRow}
			/>
		);
	}

	return (
		<div className={"flex min-h-0 flex-1 flex-col"}>
			<div className={"px-4 pt-4 pb-2"}>
				<div className={"flex items-center gap-2"}>
					<SearchBar
						value={searchTerm}
						onChange={handleSearchChange}
						searchMode={searchMode}
						onSearchModeChange={handleSearchModeChange}
						ariaLabel={"Search the schema tree"}
						isSemanticModeDisabled={embeddingsStatus !== "ready"}
						isSemanticModeLoading={embeddingsStatus === "preparing"}
						semanticModeHint={semanticModeHint}
						className={"flex-1"}
					/>
					<SelectionTreeHelp />
				</div>
				{isSemanticMode && embeddingsStatus === "failed" && (
					<StatusBanner variant={"destructive"} className={"mt-2"}>
						{semanticSearchUnavailableMessage}
					</StatusBanner>
				)}
				{isSemanticMode && semanticSearchError && (
					<StatusBanner variant={"destructive"} className={"mt-2"}>
						{semanticSearchError}
					</StatusBanner>
				)}
				{hasQueryErrors && (
					<StatusBanner variant={"destructive"} className={"mt-2"}>
						The selection query must be valid before visual editing.
					</StatusBanner>
				)}
				<div className={"flex items-center gap-1.5 pt-2"}>
					{!isSearching && (
						<>
							<TreeExpandSpacer />
							<Checkbox
								checked={allCheckedState}
								disabled={isTreeDisabled || allCounts.totalCount === 0}
								onCheckedChange={handleToggleAll}
								aria-label={"Select all"}
							/>
							<span className={"text-sm font-medium text-foreground"}>
								Select all
							</span>
						</>
					)}
					<div className={"ml-auto"}>
						<RecursionDepthStepper
							value={maxRecursionDepth}
							onChange={onRecursionDepthChange}
						/>
					</div>
				</div>
			</div>
			<div
				ref={scrollContainerRef}
				className={"min-h-0 flex-1 overflow-x-hidden overflow-y-auto px-4 pb-4"}
			>
				{treeContent}
			</div>
		</div>
	);
}

function SelectionTreeHelp() {
	return (
		<HelpButton title={"Schema Tree"} ariaLabel={"Schema tree help"}>
			<HelpItem term={"Schema Tree"}>
				check a field to add it to the Selection Query; checking a parent adds
				everything under it. A dash means only part of it is selected. The tree
				is read-only while the query is invalid.
			</HelpItem>
			<HelpItem term={"Cyclic Fields (↻)"}>
				fields whose type already appears higher up the branch. Checking one
				adds a single level. The ↻ cycle depth stepper sets how many cyclic
				fields deep a branch can be expanded; type a number or use − and +.
				Cyclic fields beyond it are greyed out and can't be selected. Lowering
				it leaves the query unchanged; selections deeper than it are flagged on
				Apply Selection.
			</HelpItem>
			<HelpItem term={"Enums, Scalars and Directives"}>
				add names to the query's @pick directive. Checking a whole group writes
				an empty list, which picks all of them.
			</HelpItem>
			<HelpItem term={"Select All"}>
				select every @pick name and every field, including cyclic fields up to
				the cycle depth, at once. To keep almost everything, select all, then
				uncheck what to exclude.
			</HelpItem>
			<HelpItem term={"Search"}>
				text search filters the tree to the fields and @pick names whose name
				contains the search text. Semantic search finds the{" "}
				{SEMANTIC_SEARCH_LIMIT} schema elements closest in meaning to what you
				type.
			</HelpItem>
			<HelpItem term={"Docs"}>
				click a field, enum or scalar name to open its documentation on the
				right.
			</HelpItem>
		</HelpButton>
	);
}
