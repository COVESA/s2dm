import type { SearchOptions } from "@ledger-ui/data/search";
import { useLedgerDispatch, useLedgerSelector } from "@ledger-ui/state/hooks";
import {
	selectSearchOptions,
	setSearchOptions,
} from "@ledger-ui/state/ledgerSlice";
import { CaseSensitive, Regex, WholeWord } from "lucide-react";
import { cn } from "@/utils/cn";

const TOGGLES: {
	option: keyof SearchOptions;
	label: string;
	Icon: typeof Regex;
}[] = [
	{ option: "caseSensitive", label: "Match case", Icon: CaseSensitive },
	{ option: "wholeWord", label: "Match whole word", Icon: WholeWord },
	{ option: "regex", label: "Use regular expression", Icon: Regex },
];

export function SearchOptionToggles() {
	const dispatch = useLedgerDispatch();
	const options = useLedgerSelector(selectSearchOptions);

	return (
		<div className="absolute top-1/2 right-1 flex -translate-y-1/2 items-center gap-0.5">
			{TOGGLES.map(({ option, label, Icon }) => (
				<button
					key={option}
					type="button"
					onClick={() =>
						dispatch(setSearchOptions({ [option]: !options[option] }))
					}
					className={cn(
						"cursor-pointer rounded p-1 text-muted-foreground transition-colors hover:bg-muted",
						// The same tint the grid and the record values use; --accent is
						// barely a shade against a light ground.
						options[option] && "bg-sky-500/10 text-foreground",
					)}
					aria-pressed={options[option]}
					title={label}
				>
					<Icon className="h-4 w-4" />
				</button>
			))}
		</div>
	);
}
