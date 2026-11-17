import type { CheckedState } from "@radix-ui/react-checkbox";
import { useId } from "react";
import {
	type CheckboxOption,
	OptionsPopover,
} from "@/components/OptionsPopover";
import {
	selectCleanBeforeResolve,
	setCleanBeforeResolve,
} from "@/store/deps/resolve/resolveSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";

type ResolveOptionsPopoverProps = {
	disabled: boolean;
};

export function ResolveOptionsPopover({
	disabled,
}: ResolveOptionsPopoverProps) {
	const dispatch = useAppDispatch();
	const cleanBeforeResolve = useAppSelector(selectCleanBeforeResolve);
	const idPrefix = useId();

	const handleCleanBeforeResolveChange = (checked: CheckedState) => {
		const cleanBeforeResolveAction = setCleanBeforeResolve(checked === true);
		dispatch(cleanBeforeResolveAction);
	};

	const resolveOptions: CheckboxOption[] = [
		{
			id: `${idPrefix}-clean-before-resolve`,
			label: "Clean before resolving",
			title: "Discard cached results before resolving",
			checked: cleanBeforeResolve,
			onCheckedChange: handleCleanBeforeResolveChange,
		},
	];

	return (
		<OptionsPopover
			title={"Resolve options"}
			disabled={disabled}
			options={resolveOptions}
		/>
	);
}
