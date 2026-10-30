import { Button } from "@shared-ui/components/button";

type ListPaginationProps = {
	shown: number;
	total: number;
	hasMore: boolean;
	pageSize: number;
	onShowMore: () => void;
};

export function ListPagination({
	shown,
	total,
	hasMore,
	pageSize,
	onShowMore,
}: ListPaginationProps) {
	if (total <= pageSize) {
		return null;
	}

	const nextCount = Math.min(pageSize, total - shown);

	return (
		<div className="flex flex-col items-center gap-2 pt-1 text-sm">
			<span className="text-muted-foreground">
				Showing {shown} of {total}
			</span>
			{hasMore && (
				<Button variant="outline" size="sm" onClick={onShowMore}>
					Show {nextCount} more
				</Button>
			)}
		</div>
	);
}
