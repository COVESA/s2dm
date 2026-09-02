import type * as React from "react";
import { cn } from "@/utils/cn";

function Table({
	className,
	containerClassName,
	containerRef,
	...props
}: React.ComponentProps<"table"> & {
	containerClassName?: string;
	containerRef?: React.Ref<HTMLDivElement>;
}) {
	return (
		<div
			ref={containerRef}
			data-slot="table-container"
			className={cn("relative w-full overflow-auto", containerClassName)}
		>
			<table
				data-slot="table"
				className={cn("w-full caption-bottom text-sm", className)}
				{...props}
			/>
		</div>
	);
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
	return (
		<thead
			data-slot="table-header"
			className={cn("[&_tr]:border-b", className)}
			{...props}
		/>
	);
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
	return (
		<tbody
			data-slot="table-body"
			className={cn("[&_tr:last-child]:border-0", className)}
			{...props}
		/>
	);
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
	return (
		<tr
			data-slot="table-row"
			className={cn(
				"border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted",
				className,
			)}
			{...props}
		/>
	);
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
	return (
		<th
			data-slot="table-head"
			className={cn(
				"sticky top-0 z-10 h-9 bg-background px-3 text-left align-middle font-medium whitespace-nowrap text-muted-foreground",
				className,
			)}
			{...props}
		/>
	);
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
	return (
		<td
			data-slot="table-cell"
			className={cn("px-3 py-2 align-middle whitespace-nowrap", className)}
			{...props}
		/>
	);
}

export { Table, TableBody, TableCell, TableHead, TableHeader, TableRow };
