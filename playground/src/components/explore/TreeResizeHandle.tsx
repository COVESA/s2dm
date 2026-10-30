import { cn } from "@shared-ui/utils/cn";
import { useRef, useState } from "react";

const DEFAULT_TREE_WIDTH_PERCENT = 25;
const MIN_TREE_WIDTH_PERCENT = 25;
const MAX_TREE_WIDTH_PERCENT = 70;

function clampTreeWidthPercent(percent: number): number {
	const boundedBelowPercent = Math.max(percent, MIN_TREE_WIDTH_PERCENT);
	return Math.min(boundedBelowPercent, MAX_TREE_WIDTH_PERCENT);
}

/**
 * Tracks the tree pane's width as a share of the split row, resizable by
 * dragging the handle or with the left and right arrow keys.
 *
 * @returns The split row ref, the current width percent, and the handle's
 * event handlers.
 */
export function useTreeResize() {
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

type TreeResizeHandleProps = {
	treeResize: ReturnType<typeof useTreeResize>;
	isHidden: boolean;
};

export function TreeResizeHandle({
	treeResize,
	isHidden,
}: TreeResizeHandleProps) {
	return (
		<hr
			className={cn(
				"m-0 h-auto w-1 shrink-0 cursor-col-resize touch-none self-stretch border-0 outline-none hover:bg-primary/30 focus-visible:bg-primary/30",
				{ hidden: isHidden },
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
	);
}
