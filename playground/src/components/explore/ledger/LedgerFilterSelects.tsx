import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { FILTERABLE_COLUMNS } from "@/ledger/modlProfile";
import { useAppDispatch } from "@/store/hooks";
import { setLedgerFilter } from "@/store/ledger/ledgerSlice";

// Radix Select reserves "" for "no selection", so "all" needs its own value.
const ALL_VALUES = "__all__";

type LedgerFilterSelectsProps = {
	filters: Record<string, string>;
	filterOptions: Record<string, string[]>;
};

export function LedgerFilterSelects({
	filters,
	filterOptions,
}: LedgerFilterSelectsProps) {
	const dispatch = useAppDispatch();

	return FILTERABLE_COLUMNS.map((column) => {
		const values = filterOptions[column];
		if (!values || values.length === 0) {
			return null;
		}
		return (
			<Select
				key={column}
				value={filters[column] ?? ALL_VALUES}
				onValueChange={(value) =>
					dispatch(
						setLedgerFilter({
							column,
							value: value === ALL_VALUES ? "" : value,
						}),
					)
				}
			>
				<SelectTrigger className="w-40 shrink-0">
					<SelectValue />
				</SelectTrigger>
				<SelectContent>
					<SelectItem value={ALL_VALUES}>
						<span>All {column}</span>
					</SelectItem>
					{values.map((value) => (
						<SelectItem key={value} value={value}>
							{value}
						</SelectItem>
					))}
				</SelectContent>
			</Select>
		);
	});
}
