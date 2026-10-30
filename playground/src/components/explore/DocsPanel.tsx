import {
	DocExplorer,
	type DocExplorerNavStack,
	useDocExplorer,
} from "@graphiql/plugin-doc-explorer";
import { Button } from "@shared-ui/components/button";
import { cn } from "@shared-ui/utils/cn";
import { X } from "lucide-react";
import { useEffect, useState } from "react";

/** The root page that `reset` leaves, plus the one page the tree opens. */
const FIRST_DOCS_PAGE_STACK_LENGTH = 2;

type DocsPanelProps = {
	isOpen: boolean;
	onClose: () => void;
};

export function DocsPanel({ isOpen, onClose }: DocsPanelProps) {
	const [docExplorerNode, setDocExplorerNode] = useState<HTMLDivElement | null>(
		null,
	);
	const docExplorerNavStack: DocExplorerNavStack = useDocExplorer();
	const isBackToDocsRoot =
		docExplorerNavStack.length <= FIRST_DOCS_PAGE_STACK_LENGTH;

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

	return (
		<div
			className={cn(
				"shrink-0 overflow-hidden border-[color:var(--color-border)] transition-[width,visibility] duration-200 ease-in-out motion-reduce:transition-none",
				{
					"visible w-[300px] border-l": isOpen,
					"invisible w-0": !isOpen,
				},
			)}
			aria-hidden={!isOpen}
		>
			<div
				ref={setDocExplorerNode}
				className={cn(
					"relative h-full w-[300px] [&_.graphiql-doc-explorer-search]:hidden!",
					{
						"[&_.graphiql-doc-explorer-back]:hidden!": isBackToDocsRoot,
					},
				)}
			>
				<Button
					type={"button"}
					variant={"ghost"}
					size={"icon-sm"}
					className={"absolute top-2 right-2 z-10"}
					onClick={onClose}
					aria-label={"Close Docs"}
					title={"Close Docs"}
				>
					<X className={"size-4"} />
				</Button>
				<DocExplorer />
			</div>
		</div>
	);
}
