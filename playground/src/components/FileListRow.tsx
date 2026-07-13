import {
	type ComponentPropsWithoutRef,
	forwardRef,
	type ReactNode,
} from "react";
import { cn } from "@/utils/cn";

type FileListRowProps = ComponentPropsWithoutRef<"li"> & {
	label: string;
	leading?: ReactNode;
	icon: ReactNode;
	trailing?: ReactNode;
};

export const FileListRow = forwardRef<HTMLLIElement, FileListRowProps>(
	function FileListRow(
		{ label, leading, icon, trailing, className, ...props },
		ref,
	) {
		return (
			<li
				ref={ref}
				className={cn(
					"group flex items-center gap-2 rounded-md border border-border bg-background/50 px-3 py-2 text-sm text-foreground transition-colors hover:bg-background/80",
					className,
				)}
				{...props}
			>
				{leading}
				{icon}
				<span className="flex-1 truncate">{label}</span>
				{trailing}
			</li>
		);
	},
);
