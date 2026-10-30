import type { LucideIcon } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type IconTabOption<T extends string> = {
	value: T;
	label: string;
	icon: LucideIcon;
};

type IconTabsProps<T extends string> = {
	options: IconTabOption<T>[];
	value: T;
	onValueChange: (value: T) => void;
	className?: string;
};

export function IconTabs<T extends string>({
	options,
	value,
	onValueChange,
	className,
}: IconTabsProps<T>) {
	const handleValueChange = (nextValue: string) => {
		const option = options.find(
			(candidateOption) => candidateOption.value === nextValue,
		);
		if (option) {
			onValueChange(option.value);
		}
	};

	return (
		<Tabs value={value} onValueChange={handleValueChange} className={className}>
			<TabsList>
				{options.map(({ value: optionValue, label, icon: Icon }) => (
					<TabsTrigger
						key={optionValue}
						value={optionValue}
						aria-label={label}
						title={label}
					>
						<Icon className={"size-4"} />
					</TabsTrigger>
				))}
			</TabsList>
		</Tabs>
	);
}
