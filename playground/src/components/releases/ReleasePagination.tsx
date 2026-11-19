import { Button } from "@shared-ui/components/button";
import type { ReactNode } from "react";
import type { ReleasePage } from "@/api/types";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";

type ReleasePaginationProps = {
	page: ReleasePage;
	isLoading: boolean;
	onPageChange: (pageNumber: number) => void;
};

export function ReleasePagination({
	page,
	isLoading,
	onPageChange,
}: ReleasePaginationProps) {
	const previousPage = page.page - 1;
	const nextPage = page.page + 1;
	const lastPage = page.last_page;

	const handlePageSelect = (pageValue: string) => {
		const selectedPage = Number(pageValue);
		onPageChange(selectedPage);
	};

	let pagePicker: ReactNode = (
		<span className={"text-xs text-muted-foreground"}>Page {page.page}</span>
	);
	if (lastPage !== null) {
		const pageValues: string[] = [];
		for (let pageNumber = 1; pageNumber <= lastPage; pageNumber++) {
			const pageValue = String(pageNumber);
			pageValues.push(pageValue);
		}
		const currentPageValue = String(page.page);

		pagePicker = (
			<div className={"flex items-center gap-1 text-xs text-muted-foreground"}>
				<span>Page</span>
				<Select
					value={currentPageValue}
					onValueChange={handlePageSelect}
					disabled={isLoading}
				>
					<SelectTrigger size={"sm"} aria-label={"Page"}>
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{pageValues.map((pageValue) => (
							<SelectItem key={pageValue} value={pageValue}>
								{pageValue}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
				<span>of {lastPage}</span>
			</div>
		);
	}

	return (
		<div
			className={"flex items-center justify-between gap-2 border-t px-3 py-2"}
		>
			<Button
				type={"button"}
				variant={"outline"}
				size={"sm"}
				disabled={!page.has_previous || isLoading}
				onClick={() => onPageChange(previousPage)}
			>
				Previous
			</Button>
			{pagePicker}
			<Button
				type={"button"}
				variant={"outline"}
				size={"sm"}
				disabled={!page.has_next || isLoading}
				onClick={() => onPageChange(nextPage)}
			>
				Next
			</Button>
		</div>
	);
}
