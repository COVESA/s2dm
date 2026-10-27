import { type IconTabOption, IconTabs } from "@shared-ui/components/icon-tabs";
import { Input } from "@shared-ui/components/input";
import { cn } from "@shared-ui/utils/cn";
import { CaseSensitive, Lightbulb, Search } from "lucide-react";
import type { ChangeEvent } from "react";

export type SearchMode = "text" | "semantic";

type SearchBarProps = {
	value: string;
	onChange: (event: ChangeEvent<HTMLInputElement>) => void;
	searchMode: SearchMode;
	onSearchModeChange: (searchMode: SearchMode) => void;
	/** Names what is being searched, for assistive technology. */
	ariaLabel: string;
	isSemanticModeDisabled?: boolean;
	/** Shows a spinner on the semantic mode while it is getting ready. */
	isSemanticModeLoading?: boolean;
	/** Hover text on the semantic mode, e.g. why it is disabled. */
	semanticModeHint?: string;
	className?: string;
};

export function SearchBar({
	value,
	onChange,
	searchMode,
	onSearchModeChange,
	ariaLabel,
	isSemanticModeDisabled = false,
	isSemanticModeLoading = false,
	semanticModeHint,
	className,
}: SearchBarProps) {
	let placeholder = "Search";
	if (searchMode === "semantic") {
		placeholder = "Semantic search";
	}
	const searchModeOptions: IconTabOption<SearchMode>[] = [
		{ value: "text", label: "Text search", icon: CaseSensitive },
		{
			value: "semantic",
			label: "Semantic search",
			icon: Lightbulb,
			isDisabled: isSemanticModeDisabled,
			isLoading: isSemanticModeLoading,
			hint: semanticModeHint,
		},
	];

	return (
		<div className={cn("relative", className)}>
			<Search
				className={
					"pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
				}
			/>
			<Input
				type={"search"}
				value={value}
				onChange={onChange}
				placeholder={placeholder}
				aria-label={ariaLabel}
				className={"pr-16 pl-8"}
			/>
			<IconTabs
				options={searchModeOptions}
				value={searchMode}
				onValueChange={onSearchModeChange}
				isCompact={true}
				className={"absolute top-1/2 right-1 -translate-y-1/2"}
			/>
		</div>
	);
}
