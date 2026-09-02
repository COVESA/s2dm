import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LEDGER_PAGE_SIZE } from "@/ledger/rows";
import { useAppDispatch } from "@/store/hooks";
import { setLedgerPage } from "@/store/ledger/ledgerSlice";

type LedgerTableFooterProps = {
	total: number;
	page: number;
	isLoadingRows: boolean;
	matchingLabel: string;
};

export function LedgerTableFooter({
	total,
	page,
	isLoadingRows,
	matchingLabel,
}: LedgerTableFooterProps) {
	const dispatch = useAppDispatch();
	const pageCount = Math.max(1, Math.ceil(total / LEDGER_PAGE_SIZE));
	const firstRow = total === 0 ? 0 : page * LEDGER_PAGE_SIZE + 1;
	const lastRow = Math.min(total, (page + 1) * LEDGER_PAGE_SIZE);

	return (
		<div className="flex items-center justify-between gap-3 border-t px-6 py-3">
			<span className="text-sm text-muted-foreground tabular-nums">
				{firstRow}–{lastRow} of {total}
				{matchingLabel}
				{pageCount > 1 && (
					<span className="ml-2">· Sorting applies to this page only</span>
				)}
			</span>
			<div className="flex items-center gap-2">
				<span className="text-sm text-muted-foreground tabular-nums">
					Page {page + 1} of {pageCount}
				</span>
				<Button
					variant="outline"
					size="icon"
					onClick={() => dispatch(setLedgerPage(page - 1))}
					disabled={page === 0 || isLoadingRows}
					aria-label="Previous page"
					title="Previous page"
				>
					<ChevronLeft className="h-4 w-4" />
				</Button>
				<Button
					variant="outline"
					size="icon"
					onClick={() => dispatch(setLedgerPage(page + 1))}
					disabled={page + 1 >= pageCount || isLoadingRows}
					aria-label="Next page"
					title="Next page"
				>
					<ChevronRight className="h-4 w-4" />
				</Button>
			</div>
		</div>
	);
}
