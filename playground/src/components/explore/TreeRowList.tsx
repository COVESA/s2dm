import { useVirtualizer } from "@tanstack/react-virtual";
import type { ReactNode, RefObject } from "react";
import { TREE_ROW_HEIGHT_PX } from "@/components/explore/TreeRowParts";
import {
	getStickyRowIndexes,
	type TreeRow,
} from "@/utils/selectionQuery/treeRows";

const OVERSCAN_ROW_COUNT = 10;

type TreeRowListProps = {
	rows: TreeRow[];
	scrollContainerRef: RefObject<HTMLDivElement>;
	renderRow: (rowIndex: number) => ReactNode;
};

export function TreeRowList({
	rows,
	scrollContainerRef,
	renderRow,
}: TreeRowListProps) {
	const rowVirtualizer = useVirtualizer({
		count: rows.length,
		getScrollElement: () => scrollContainerRef.current,
		estimateSize: () => TREE_ROW_HEIGHT_PX,
		getItemKey: (index) => rows[index].key,
		overscan: OVERSCAN_ROW_COUNT,
	});

	const scrollOffset = rowVirtualizer.scrollOffset ?? 0;
	const firstVisibleIndex = Math.floor(scrollOffset / TREE_ROW_HEIGHT_PX);
	const stickyRowIndexes = getStickyRowIndexes(rows, firstVisibleIndex);
	const stickyHeight = stickyRowIndexes.length * TREE_ROW_HEIGHT_PX;
	const stickyOverlap = -stickyHeight;
	const virtualRows = rowVirtualizer.getVirtualItems();
	const totalHeight = rowVirtualizer.getTotalSize();

	return (
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
