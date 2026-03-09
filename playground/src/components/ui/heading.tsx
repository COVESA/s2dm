import type { VariantProps } from "class-variance-authority";
import { cva } from "class-variance-authority";
import type * as React from "react";
import { cn } from "@/lib/utils";

const headingVariants = cva("font-bold text-foreground", {
	variants: {
		level: {
			h1: "text-4xl",
			h2: "text-2xl",
			h3: "text-lg",
			h4: "text-base",
		},
	},
	defaultVariants: {
		level: "h2",
	},
});

export interface HeadingProps
	extends React.HTMLAttributes<HTMLHeadingElement>,
		VariantProps<typeof headingVariants> {
	level?: "h1" | "h2" | "h3" | "h4";
}

export function Heading({
	className,
	level = "h2",
	children,
	...props
}: HeadingProps) {
	const Comp = level;

	return (
		<Comp className={cn(headingVariants({ level, className }))} {...props}>
			{children}
		</Comp>
	);
}
