import { ListFilter } from "lucide-react";
import { type ComponentPropsWithoutRef, forwardRef } from "react";
import type { InstancePickPopoverProps } from "@/components/explore/instancePick/InstancePickPopover";
import { Button } from "@/components/ui/button";
import { cn } from "@/utils/cn";

type InstancePickTriggerProps = ComponentPropsWithoutRef<"button"> &
	Pick<InstancePickPopoverProps, "isDisabled"> & {
		label: string;
		pickedCount: number;
		totalCount: number;
	};

export const InstancePickTrigger = forwardRef<
	HTMLButtonElement,
	InstancePickTriggerProps
>(function InstancePickTrigger(
	{ label, pickedCount, totalCount, isDisabled, ...triggerProps },
	ref,
) {
	const isNarrowed = pickedCount < totalCount;

	return (
		<Button
			{...triggerProps}
			ref={ref}
			type={"button"}
			variant={"ghost"}
			size={"icon-sm"}
			className={cn(
				"h-5 w-auto min-w-5 shrink-0 gap-0.5 px-1 text-muted-foreground",
				{ "text-foreground": isNarrowed },
			)}
			disabled={isDisabled}
			aria-label={`Pick ${label}`}
		>
			<ListFilter className={"size-3.5"} />
			{isNarrowed && (
				<span className={"font-mono text-xs"}>
					{pickedCount}/{totalCount}
				</span>
			)}
		</Button>
	);
});
