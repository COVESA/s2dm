import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@shared-ui/utils/cn";
import * as React from "react";

const Tabs = TabsPrimitive.Root;

const TAB_SELECTOR = '[role="tab"]';
const ACTIVE_TAB_SELECTOR = `${TAB_SELECTOR}[data-state="active"]`;

type IndicatorBox = {
	left: number;
	top: number;
	width: number;
	height: number;
};

/**
 * Tracks the position and size of the selected tab in a tab list.
 * The box updates when the selected tab changes.
 * It also updates when the list or a tab changes size.
 * @param listRef - Ref to the tab list element.
 * @returns The box of the selected tab, or null when no tab is selected.
 *   Also a flag that turns true one frame after the first measurement.
 */
function useActiveTabBox(listRef: React.RefObject<HTMLElement | null>): {
	indicatorBox: IndicatorBox | null;
	canAnimate: boolean;
} {
	const [indicatorBox, setIndicatorBox] = React.useState<IndicatorBox | null>(
		null,
	);
	const [canAnimate, setCanAnimate] = React.useState(false);

	React.useLayoutEffect(() => {
		const listElement = listRef.current;
		if (!listElement) {
			return;
		}

		const moveIndicator = () => {
			const activeTab =
				listElement.querySelector<HTMLElement>(ACTIVE_TAB_SELECTOR);
			if (!activeTab) {
				setIndicatorBox(null);
				return;
			}
			setIndicatorBox({
				left: activeTab.offsetLeft,
				top: activeTab.offsetTop,
				width: activeTab.offsetWidth,
				height: activeTab.offsetHeight,
			});
		};

		moveIndicator();
		const animationFrame = requestAnimationFrame(() => {
			setCanAnimate(true);
		});

		const stateObserver = new MutationObserver(moveIndicator);
		stateObserver.observe(listElement, {
			subtree: true,
			attributeFilter: ["data-state"],
		});
		const sizeObserver = new ResizeObserver(moveIndicator);
		sizeObserver.observe(listElement);
		const tabElements = listElement.querySelectorAll(TAB_SELECTOR);
		for (const tabElement of tabElements) {
			sizeObserver.observe(tabElement);
		}

		return () => {
			cancelAnimationFrame(animationFrame);
			stateObserver.disconnect();
			sizeObserver.disconnect();
		};
	}, [listRef]);

	return { indicatorBox, canAnimate };
}

/**
 * A row of tabs with one highlight behind the selected tab. The highlight
 * slides to a newly selected tab. It also follows size changes of the tabs.
 */
const TabsList = React.forwardRef<
	React.ElementRef<typeof TabsPrimitive.List>,
	React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, children, ...props }, ref) => {
	const listRef = React.useRef<HTMLDivElement>(null);
	const { indicatorBox, canAnimate } = useActiveTabBox(listRef);

	React.useImperativeHandle(ref, () => listRef.current as HTMLDivElement);

	let indicatorStyle: React.CSSProperties | undefined;
	if (indicatorBox) {
		indicatorStyle = {
			top: indicatorBox.top,
			width: indicatorBox.width,
			height: indicatorBox.height,
			transform: `translateX(${indicatorBox.left}px)`,
		};
	}

	return (
		<TabsPrimitive.List
			ref={listRef}
			className={cn(
				"relative inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground",
				className,
			)}
			{...props}
		>
			{indicatorBox && (
				<span
					aria-hidden="true"
					className={cn(
						"pointer-events-none absolute left-0 rounded-md bg-background shadow",
						canAnimate &&
							"transition-[transform,width] duration-200 ease-out motion-reduce:transition-none",
					)}
					style={indicatorStyle}
				/>
			)}
			{children}
		</TabsPrimitive.List>
	);
});
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef<
	React.ElementRef<typeof TabsPrimitive.Trigger>,
	React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
	<TabsPrimitive.Trigger
		ref={ref}
		className={cn(
			"relative z-10 inline-flex cursor-pointer items-center justify-center whitespace-nowrap rounded-md border-0 bg-transparent px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:text-foreground",
			className,
		)}
		{...props}
	/>
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
	React.ElementRef<typeof TabsPrimitive.Content>,
	React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
	<TabsPrimitive.Content
		ref={ref}
		className={cn(
			"mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
			className,
		)}
		{...props}
	/>
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
