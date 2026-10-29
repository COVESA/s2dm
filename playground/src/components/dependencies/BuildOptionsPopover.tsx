import type { CheckedState } from "@radix-ui/react-checkbox";
import { ChevronUp } from "lucide-react";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { FormLabel } from "@/components/ui/form-label";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import {
	selectAutoPrefix,
	selectPreserveQueryType,
	setAutoPrefix,
	setPreserveQueryType,
} from "@/store/deps/compose/composeSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";

type BuildOptionsPopoverProps = {
	disabled: boolean;
};

export function BuildOptionsPopover({ disabled }: BuildOptionsPopoverProps) {
	const dispatch = useAppDispatch();
	const autoPrefix = useAppSelector(selectAutoPrefix);
	const preserveQueryType = useAppSelector(selectPreserveQueryType);
	const idPrefix = useId();

	const handleAutoPrefixChange = (checked: CheckedState) => {
		const autoPrefixAction = setAutoPrefix(checked === true);
		dispatch(autoPrefixAction);
	};

	const handlePreserveQueryTypeChange = (checked: CheckedState) => {
		const preserveQueryTypeAction = setPreserveQueryType(checked === true);
		dispatch(preserveQueryTypeAction);
	};

	const buildOptions = [
		{
			id: `${idPrefix}-auto-prefix`,
			label: "Auto-prefix conflicting types",
			title: "Prefix conflicting dependency types using preferred_prefix",
			checked: autoPrefix,
			onCheckedChange: handleAutoPrefixChange,
		},
		{
			id: `${idPrefix}-preserve-query-type`,
			label: "Keep Query type",
			title: "Keep the composed Query type in the built schema",
			checked: preserveQueryType,
			onCheckedChange: handlePreserveQueryTypeChange,
		},
	];

	return (
		<Popover>
			<PopoverTrigger asChild={true}>
				<Button
					variant={"outline"}
					size={"icon-sm"}
					disabled={disabled}
					title={"Build options"}
					className={"rounded-l-none border-l-0"}
				>
					<ChevronUp className={"h-4 w-4"} />
				</Button>
			</PopoverTrigger>
			<PopoverContent side={"top"} align={"end"} className={"w-64 p-0"}>
				<ul className={"divide-y"}>
					{buildOptions.map((buildOption) => (
						<li
							key={buildOption.id}
							className={"flex items-center gap-3 px-4 py-3"}
							title={buildOption.title}
						>
							<FormLabel
								htmlFor={buildOption.id}
								className={"flex-1 cursor-pointer text-sm"}
							>
								{buildOption.label}
							</FormLabel>
							<Checkbox
								id={buildOption.id}
								checked={buildOption.checked}
								disabled={disabled}
								onCheckedChange={buildOption.onCheckedChange}
							/>
						</li>
					))}
				</ul>
			</PopoverContent>
		</Popover>
	);
}
