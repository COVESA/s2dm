import {
	type DocExplorerNavStackItem,
	useDocExplorerActions,
} from "@graphiql/plugin-doc-explorer";
import { useGraphiQL } from "@graphiql/react";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
	type GraphQLObjectType,
	type GraphQLSchema,
	isInterfaceType,
	isObjectType,
} from "graphql";
import { Search } from "lucide-react";
import {
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
import {
	TREE_ROW_HEIGHT_PX,
	TreeExpandSpacer,
} from "@/components/explore/TreeRowParts";
import { HelpButton, HelpItem } from "@/components/HelpButton";
import type { ValidatedQuery } from "@/components/QueryEditorWrapper";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { StatusBanner } from "@/components/ui/status-banner";
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
import { readSelection } from "@/utils/selectionQuery/readSelection";
import {
	createRootNode,
	DEFAULT_RECURSION_DEPTH,
	type SchemaTreeNode,
} from "@/utils/selectionQuery/schemaTree";
import {
	listSearchableNodes,
	matchesSearchTerm,
	normalizeSearchTerm,
	searchTree,
} from "@/utils/selectionQuery/searchTree";
import {
	buildTreeRows,
	getStickyRowIndexes,
} from "@/utils/selectionQuery/treeRows";

const PICK_GROUP_LABELS: Record<PickArgumentName, string> = {
	enums: "Enums",
	scalars: "Scalars",
	directives: "Directives",
};

const PICK_GROUPS = PICK_ARGUMENT_NAMES.map((argumentName) => ({
	argumentName,
	label: PICK_GROUP_LABELS[argumentName],
}));

const OVERSCAN_ROW_COUNT = 10;

type SelectionTreeProps = {
	selectionQuery: string;
	validatedQuery: ValidatedQuery;
	hasQueryErrors: boolean;
	onTreeEdit: (text: string) => void;
	onOpenDocs: () => void;
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
	hasQueryErrors,
	onTreeEdit,
	onOpenDocs,
	schema,
	queryType,
}: SelectionTreeContentProps) {
	const [isUpdating, setIsUpdating] = useState(false);
	const [expandedKeys, setExpandedKeys] = useState<Set<string>>(
		() => new Set(),
	);
	const [searchTerm, setSearchTerm] = useState("");
	const [maxRecursionDepth, setMaxRecursionDepth] = useState(
		DEFAULT_RECURSION_DEPTH,
	);
	const scrollContainerRef = useRef<HTMLDivElement>(null);
	const docExplorerActions = useDocExplorerActions();

	const selection = useMemo(
		() => readSelection(validatedQuery.document),
		[validatedQuery.document],
	);
	const countLeaves = useMemo(() => createLeafCounter(selection), [selection]);
	const rootNode = useMemo(() => createRootNode(queryType), [queryType]);

	const deferredSearchTerm = useDeferredValue(searchTerm);
	const normalizedSearchTerm = normalizeSearchTerm(deferredSearchTerm);
	const isSearching = normalizedSearchTerm.length > 0;
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
		return searchTree(searchableNodes, normalizedSearchTerm);
	}, [searchableNodes, normalizedSearchTerm, isSearching]);

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
				if (isSearching) {
					const matchingNameList = pickGroup.names.filter((name) =>
						matchesSearchTerm(name, normalizedSearchTerm),
					);
					matchingNames = new Set(matchingNameList);
				}
				return { ...pickGroup, matchingNames };
			}),
		[pickGroupNames, isSearching, normalizedSearchTerm],
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
	const rowVirtualizer = useVirtualizer({
		count: rows.length,
		getScrollElement: () => scrollContainerRef.current,
		estimateSize: () => TREE_ROW_HEIGHT_PX,
		getItemKey: (index) => rows[index].key,
		overscan: OVERSCAN_ROW_COUNT,
	});

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

	const scrollOffset = rowVirtualizer.scrollOffset ?? 0;
	const firstVisibleIndex = Math.floor(scrollOffset / TREE_ROW_HEIGHT_PX);
	const stickyRowIndexes = getStickyRowIndexes(rows, firstVisibleIndex);
	const stickyHeight = stickyRowIndexes.length * TREE_ROW_HEIGHT_PX;
	const stickyOverlap = -stickyHeight;
	const virtualRows = rowVirtualizer.getVirtualItems();
	const totalHeight = rowVirtualizer.getTotalSize();

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

	let treeContent: ReactNode = <EmptyState title={"No matches"} />;
	if (!hasNoMatches) {
		treeContent = (
			<>
				{stickyRowIndexes.length > 0 && (
					<div
						className={"sticky top-0 z-10 bg-background shadow-sm"}
						style={{ height: stickyHeight, marginBottom: stickyOverlap }}
					>
						{stickyRowIndexes.map((rowIndex) => (
							<div key={rows[rowIndex].key}>{renderRow(rowIndex)}</div>
						))}
					</div>
				)}
				<div className={"relative"} style={{ height: totalHeight }}>
					{virtualRows.map((virtualRow) => {
						const rowTransform = `translateY(${virtualRow.start}px)`;
						return (
							<div
								key={virtualRow.key}
								className={"absolute top-0 left-0 w-full"}
								style={{ height: virtualRow.size, transform: rowTransform }}
							>
								{renderRow(virtualRow.index)}
							</div>
						);
					})}
				</div>
			</>
		);
	}

	return (
		<div className={"flex min-h-0 flex-1 flex-col"}>
			<div className={"px-4 pt-4 pb-2"}>
				<div className={"flex items-center gap-2"}>
					<div className={"relative flex-1"}>
						<Search
							className={
								"pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
							}
						/>
						<Input
							type={"search"}
							value={searchTerm}
							onChange={(event) => setSearchTerm(event.target.value)}
							placeholder={"Search"}
							aria-label={"Search the schema tree"}
							className={"pl-8"}
						/>
					</div>
					<SelectionTreeHelp />
				</div>
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
							onChange={setMaxRecursionDepth}
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
				Cyclic fields beyond it are greyed out and can't be selected.
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
				filter the tree to the fields and @pick names whose name contains the
				search text.
			</HelpItem>
			<HelpItem term={"Docs"}>
				click a field, enum or scalar name to open its documentation on the
				right.
			</HelpItem>
		</HelpButton>
	);
}
