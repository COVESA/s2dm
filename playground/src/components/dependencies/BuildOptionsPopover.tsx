import type { CheckedState } from "@radix-ui/react-checkbox";
import { useId } from "react";
import {
	type CheckboxOption,
	OptionsPopover,
} from "@/components/OptionsPopover";
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

	const buildOptions: CheckboxOption[] = [
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
		<OptionsPopover
			title={"Build options"}
			disabled={disabled}
			options={buildOptions}
		/>
	);
}
