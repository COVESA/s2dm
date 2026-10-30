import Link from "@docusaurus/Link";
import {
	type GlobalDoc,
	useAllDocsData,
} from "@docusaurus/plugin-content-docs/client";
import { useLocation } from "@docusaurus/router";
import useBaseUrl from "@docusaurus/useBaseUrl";
import { slugify } from "@graphql-markdown/utils/string";
import { SearchBar, type SearchMode } from "@search-ui/components/SearchBar";
import {
	SEMANTIC_SEARCH_DEBOUNCE_MS,
	SEMANTIC_SEARCH_LIMIT,
} from "@search-ui/constants";
import { splitElementId } from "@search-ui/utils/elementId";
import { Fragment, type ReactNode, useEffect, useState } from "react";
import {
	createSemanticSearch,
	type SemanticSearch,
} from "@/semantic-search/createSemanticSearch";
import { cn } from "@shared-ui/utils/cn";
import { filterElementIdsByName, loadElementIds } from "@/utils/elementIds";
import { getErrorMessage } from "@/utils/getErrorMessage";

const TEXT_SEARCH_LIMIT = 50;

// Pages that graphql-markdown generates for named types live under this doc id prefix.
const ELEMENT_DOC_ID_PREFIX = "elements/types/";

const MUTED_TEXT_CLASS = "text-(--ifm-color-emphasis-700)";

type SearchResult = {
	elementIds: string[];
	/** Matches before the result limit was applied. */
	totalCount: number;
};

type SearchState =
	| { status: "idle" }
	| { status: "searching" }
	| ({ status: "done" } & SearchResult)
	| { status: "failed"; message: string };

type LoadCache<T> = { current: Promise<T> | null };

// Module-level, so the loads survive the panel unmounting when the reader leaves the docs pages.
const elementIdsCache: LoadCache<string[]> = { current: null };
const semanticSearchCache: LoadCache<SemanticSearch> = { current: null };

/**
 * Start a load on the first call and share it with later calls. A failed load is dropped, so the
 * next call starts it again.
 *
 * @param cache - Holds the shared load. This function sets and clears it.
 * @param load - Starts the load.
 * @returns The shared load.
 */
function loadOnce<T>(
	cache: LoadCache<T>,
	load: () => Promise<T>,
): Promise<T> {
	if (!cache.current) {
		cache.current = load().catch((error: unknown) => {
			cache.current = null;
			throw error;
		});
	}
	return cache.current;
}

/**
 * Load the semantic search once per page session.
 *
 * @param embeddingsUrl - URL of the site's `embeddings.json`.
 * @returns The shared semantic search.
 */
function loadSemanticSearch(embeddingsUrl: string): Promise<SemanticSearch> {
	return loadOnce(semanticSearchCache, () =>
		createSemanticSearch(embeddingsUrl),
	);
}

/**
 * Find the docs page of an element, using the slugs graphql-markdown gives pages and headings.
 *
 * @param typeName - The element's type.
 * @param memberName - The element's field or enum value, or `undefined` for the type itself.
 * @param docs - The docs of the current version.
 * @returns The page path, with the member's heading anchor when there is one, or `null` when no
 *   page exists for the type.
 */
function findElementHref(
	typeName: string,
	memberName: string | undefined,
	docs: readonly GlobalDoc[],
): string | null {
	const typeSlug = slugify(typeName);
	const typeDoc = docs.find(
		(doc) =>
			doc.id.startsWith(ELEMENT_DOC_ID_PREFIX) &&
			doc.id.endsWith(`/${typeSlug}`),
	);
	if (!typeDoc) {
		return null;
	}
	if (!memberName) {
		return typeDoc.path;
	}
	return `${typeDoc.path}#${slugify(memberName)}`;
}

/**
 * Let a long schema name wrap after its underscores instead of mid-word.
 *
 * @param name - A type or member name, e.g. `Base_a_b`.
 * @returns The name with a line-break opportunity after each underscore.
 */
function withUnderscoreBreaks(name: string): ReactNode {
	const segments = name.split(/(?<=_)/);
	let offset = 0;
	return segments.map((segment) => {
		const key = offset;
		offset += segment.length;
		return (
			<Fragment key={key}>
				{segment}
				<wbr />
			</Fragment>
		);
	});
}

type SearchResultRowProps = {
	elementId: string;
	docs: readonly GlobalDoc[];
	currentHref: string;
};

function SearchResultRow({
	elementId,
	docs,
	currentHref,
}: SearchResultRowProps) {
	const { typeName, memberName } = splitElementId(elementId);
	const href = findElementHref(typeName, memberName, docs);
	const label = (
		<span className={"block min-w-0"}>
			<span className={"block font-semibold"}>
				{withUnderscoreBreaks(memberName ?? typeName)}
			</span>
			{memberName && (
				<span className={cn("block text-xs", MUTED_TEXT_CLASS)}>
					{withUnderscoreBreaks(typeName)}
				</span>
			)}
		</span>
	);

	if (!href) {
		return <li className={"menu__list-item px-3 py-1.5 text-sm"}>{label}</li>;
	}
	return (
		<li className={"menu__list-item"}>
			<Link
				to={href}
				className={cn(
					"menu__link text-sm",
					href === currentHref && "menu__link--active",
				)}
			>
				{label}
			</Link>
		</li>
	);
}

export function ElementSearchPanel(): ReactNode {
	const embeddingsUrl = useBaseUrl("/embeddings.json");
	const introspectionUrl = useBaseUrl("/introspection.json");
	const allDocsData = useAllDocsData();
	const location = useLocation();
	const [searchMode, setSearchMode] = useState<SearchMode>("text");
	const [query, setQuery] = useState("");
	const [searchState, setSearchState] = useState<SearchState>({
		status: "idle",
	});

	const handleSearchModeChange = (nextSearchMode: SearchMode) => {
		setSearchMode(nextSearchMode);
		if (nextSearchMode !== "semantic") {
			return;
		}
		// Load the embeddings and the model now, so the first query does not wait for them.
		loadSemanticSearch(embeddingsUrl).catch(() => {
			// The search loads again and reports the failure.
		});
	};

	useEffect(() => {
		const trimmedQuery = query.trim();
		if (!trimmedQuery) {
			setSearchState({ status: "idle" });
			return;
		}

		const searchByText = async (): Promise<SearchResult> => {
			const elementIds = await loadOnce(elementIdsCache, () =>
				loadElementIds(introspectionUrl),
			);
			const matchingIds = filterElementIdsByName(elementIds, trimmedQuery);
			return {
				elementIds: matchingIds.slice(0, TEXT_SEARCH_LIMIT),
				totalCount: matchingIds.length,
			};
		};
		const searchSemantically = async (): Promise<SearchResult> => {
			const semanticSearch = await loadSemanticSearch(embeddingsUrl);
			const elementIds = await semanticSearch.search(
				trimmedQuery,
				SEMANTIC_SEARCH_LIMIT,
			);
			return { elementIds, totalCount: elementIds.length };
		};

		let isCurrent = true;
		let delay = 0;
		let runSearch = searchByText;
		if (searchMode === "semantic") {
			delay = SEMANTIC_SEARCH_DEBOUNCE_MS;
			runSearch = searchSemantically;
		}
		const timer = setTimeout(async () => {
			setSearchState({ status: "searching" });
			let nextState: SearchState;
			try {
				const result = await runSearch();
				nextState = { status: "done", ...result };
			} catch (error) {
				const message = getErrorMessage(error);
				nextState = { status: "failed", message };
			}
			if (isCurrent) {
				setSearchState(nextState);
			}
		}, delay);
		return () => {
			isCurrent = false;
			clearTimeout(timer);
		};
	}, [query, searchMode, embeddingsUrl, introspectionUrl]);

	const latestVersion = allDocsData.default?.versions.find(
		(version) => version.isLast,
	);
	const docs = latestVersion?.docs ?? [];
	const currentHref = `${location.pathname}${location.hash}`;

	let searchingMessage = "Searching…";
	if (searchMode === "semantic") {
		searchingMessage =
			"Searching… The first semantic search downloads the search model.";
	}

	let statusMessage: string | null = null;
	if (searchState.status === "searching") {
		statusMessage = searchingMessage;
	} else if (searchState.status === "done" && searchState.totalCount === 0) {
		statusMessage = "No matches.";
	}

	let results: ReactNode = null;
	if (statusMessage) {
		results = (
			<p className={cn("m-0 px-3 py-1.5 text-sm", MUTED_TEXT_CLASS)}>
				{statusMessage}
			</p>
		);
	} else if (searchState.status === "failed") {
		results = (
			<div className={"alert alert--danger px-3 py-2 text-sm"} role={"alert"}>
				Search failed: {searchState.message}
			</div>
		);
	} else if (searchState.status === "done") {
		const isTruncated = searchState.totalCount > searchState.elementIds.length;
		results = (
			<>
				{isTruncated && (
					<p className={cn("m-0 px-3 pb-1 text-xs", MUTED_TEXT_CLASS)}>
						Showing {searchState.elementIds.length} of {searchState.totalCount}{" "}
						matches.
					</p>
				)}
				<ul className={"menu__list"} aria-label={"Search results"}>
					{searchState.elementIds.map((elementId) => (
						<SearchResultRow
							key={elementId}
							elementId={elementId}
							docs={docs}
							currentHref={currentHref}
						/>
					))}
				</ul>
			</>
		);
	}

	return (
		<div className={"border-b border-(--ifm-toc-border-color) p-2"}>
			<SearchBar
				value={query}
				onChange={(event) => setQuery(event.target.value)}
				searchMode={searchMode}
				onSearchModeChange={handleSearchModeChange}
				ariaLabel={"Search schema elements"}
			/>
			{results && (
				<div className={"mt-2 max-h-[45vh] overflow-y-auto"}>{results}</div>
			)}
		</div>
	);
}
