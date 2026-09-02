import { Search } from "lucide-react";
import { SearchOptionToggles } from "@/components/explore/ledger/SearchOptionToggles";
import { Input } from "@/components/ui/input";

type LedgerSearchInputProps = {
	value: string;
	onChange: (value: string) => void;
	// Used as both the placeholder and the accessible name.
	label: string;
};

export function LedgerSearchInput({
	value,
	onChange,
	label,
}: LedgerSearchInputProps) {
	return (
		<div className="relative w-full">
			<Search className="absolute top-1/2 left-2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
			<Input
				value={value}
				onChange={(event) => onChange(event.target.value)}
				placeholder={label}
				className="pl-8 pr-24"
				aria-label={label}
			/>
			<SearchOptionToggles />
		</div>
	);
}
