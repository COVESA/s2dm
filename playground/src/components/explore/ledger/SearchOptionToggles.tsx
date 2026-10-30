import { CaseSensitive, Regex, WholeWord } from "lucide-react";
import type { SearchMode } from "@/ledger/search";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	selectSearchOptions,
	setSearchOptions,
} from "@/store/ledger/ledgerSlice";
import { cn } from "@/utils/cn";

const MODE_TOGGLES: {
	mode: SearchMode;
	label: string;
	Icon: typeof Regex;
}[] = [
	{ mode: "wholeWord", label: "Match whole word", Icon: WholeWord },
	{ mode: "regex", label: "Use regular expression", Icon: Regex },
];

export function SearchOptionToggles() {
	const dispatch = useAppDispatch();
	const options = useAppSelector(selectSearchOptions);

	const toggleClass = (active: boolean) =>
		cn(
			"cursor-pointer rounded p-1 text-muted-foreground transition-colors hover:bg-muted",
			active && "bg-accent text-accent-foreground",
		);

	return (
		<div className="absolute top-1/2 right-1 flex -translate-y-1/2 items-center gap-0.5">
			<button
				type="button"
				onClick={() =>
					dispatch(setSearchOptions({ caseSensitive: !options.caseSensitive }))
				}
				className={toggleClass(options.caseSensitive)}
				aria-pressed={options.caseSensitive}
				title="Match case"
			>
				<CaseSensitive className="h-4 w-4" />
			</button>

			{MODE_TOGGLES.map(({ mode, label, Icon }) => (
				<button
					key={mode}
					type="button"
					onClick={() =>
						dispatch(
							setSearchOptions({
								mode: options.mode === mode ? "substring" : mode,
							}),
						)
					}
					className={toggleClass(options.mode === mode)}
					aria-pressed={options.mode === mode}
					title={label}
				>
					<Icon className="h-4 w-4" />
				</button>
			))}
		</div>
	);
}
