import { Tabs, TabsList, TabsTrigger } from "@shared-ui/components/tabs";
import { cn } from "@shared-ui/utils/cn";
import { Loader2, type LucideIcon } from "lucide-react";

export type IconTabOption<T extends string> = {
	value: T;
	label: string;
	icon: LucideIcon;
	isDisabled?: boolean;
	/** Shows a spinner in place of the icon while the option is getting ready. */
	isLoading?: boolean;
	/** Hover text in place of the label, e.g. why the option is disabled. */
	hint?: string;
};

type IconTabsProps<T extends string> = {
	options: IconTabOption<T>[];
	value: T;
	onValueChange: (value: T) => void;
	className?: string;
	/** Shrinks the switcher to fit inside a text input. */
	isCompact?: boolean;
};

export function IconTabs<T extends string>({
	options,
	value,
	onValueChange,
	className,
	isCompact = false,
}: IconTabsProps<T>) {
	const handleValueChange = (nextValue: string) => {
		const option = options.find(
			(candidateOption) => candidateOption.value === nextValue,
		);
		if (option && !option.isDisabled) {
			onValueChange(option.value);
		}
	};

	return (
		<Tabs value={value} onValueChange={handleValueChange} className={className}>
			<TabsList className={cn(isCompact && "h-7 p-0.5")}>
				{options.map(
					({
						value: optionValue,
						label,
						icon: Icon,
						isDisabled,
						isLoading,
						hint,
					}) => (
						<TabsTrigger
							key={optionValue}
							value={optionValue}
							aria-disabled={isDisabled}
							aria-label={label}
							title={hint ?? label}
							className={cn(
								isCompact && "px-1.5 py-0.5",
								isDisabled && "cursor-not-allowed opacity-50",
							)}
						>
							{isLoading && <Loader2 className={"size-4 animate-spin"} />}
							{!isLoading && <Icon className={"size-4"} />}
						</TabsTrigger>
					),
				)}
			</TabsList>
		</Tabs>
	);
}
