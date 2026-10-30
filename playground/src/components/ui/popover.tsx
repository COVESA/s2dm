import { cn } from "@shared-ui/utils/cn";
import { Popover as PopoverPrimitive } from "radix-ui";
import type * as React from "react";

function Popover({
	...props
}: React.ComponentProps<typeof PopoverPrimitive.Root>) {
	return <PopoverPrimitive.Root {...props} />;
}

function PopoverTrigger({
	...props
}: React.ComponentProps<typeof PopoverPrimitive.Trigger>) {
	return <PopoverPrimitive.Trigger data-slot={"popover-trigger"} {...props} />;
}

function PopoverContent({
	className,
	children,
	sideOffset = 8,
	...props
}: React.ComponentProps<typeof PopoverPrimitive.Content>) {
	return (
		<PopoverPrimitive.Portal>
			<PopoverPrimitive.Content
				data-slot={"popover-content"}
				sideOffset={sideOffset}
				className={cn(
					"bg-popover text-popover-foreground data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=top]:slide-in-from-bottom-2 data-[side=bottom]:slide-in-from-top-2 z-50 rounded-xl border shadow-lg outline-hidden",
					className,
				)}
				{...props}
			>
				{children}
				<PopoverPrimitive.Arrow
					className={"fill-popover drop-shadow-sm"}
					width={14}
					height={7}
				/>
			</PopoverPrimitive.Content>
		</PopoverPrimitive.Portal>
	);
}

export { Popover, PopoverContent, PopoverTrigger };
