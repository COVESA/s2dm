import type { CheckedState } from "@radix-ui/react-checkbox";
import { Button } from "@shared-ui/components/button";
import { Layers } from "lucide-react";
import { useId } from "react";
import { CliCommandDisplay } from "@/components/CliCommandDisplay";
import {
	type CheckboxOption,
	OptionsPopover,
} from "@/components/OptionsPopover";
import { selectHasComposedDependenciesSchema } from "@/store/deps/compose/composeSlice";
import { selectExploringDependencyId } from "@/store/exploration/explorationSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	selectIncludeBuiltDependencies,
	selectSourceFiles,
	setIncludeBuiltDependencies,
} from "@/store/schema/schemaSlice";
import {
	selectIsValidating,
	validateAndCompose,
} from "@/store/validation/validationSlice";

/**
 * The "Compose and Validate" icon button and its options button.
 */
export function ComposeActions() {
	const dispatch = useAppDispatch();
	const hasBuiltDependenciesSchema = useAppSelector(
		selectHasComposedDependenciesSchema,
	);
	const includeBuiltDependencies = useAppSelector(
		selectIncludeBuiltDependencies,
	);
	const isValidating = useAppSelector(selectIsValidating);
	const exploringDependencyId = useAppSelector(selectExploringDependencyId);
	const isExploringDependency = exploringDependencyId !== null;
	const idPrefix = useId();

	const handleCompose = () => {
		dispatch(validateAndCompose());
	};

	const handleIncludeBuiltDependenciesChange = (checked: CheckedState) => {
		const includeAction = setIncludeBuiltDependencies(checked === true);
		dispatch(includeAction);
	};

	let includeBuiltDependenciesTitle: string | undefined;
	if (!hasBuiltDependenciesSchema) {
		includeBuiltDependenciesTitle =
			"Build dependencies in the Dependencies tab before including them in composition.";
	}

	const composeOptions: CheckboxOption[] = [
		{
			id: `${idPrefix}-include-built-dependencies`,
			label: "Include built dependencies in composition",
			title: includeBuiltDependenciesTitle,
			checked: includeBuiltDependencies,
			disabled: !hasBuiltDependenciesSchema,
			onCheckedChange: handleIncludeBuiltDependenciesChange,
		},
	];

	return (
		<div className={"flex items-center"}>
			<Button
				variant={"outline"}
				size={"icon-sm"}
				className={"rounded-r-none"}
				onClick={handleCompose}
				loading={isValidating}
				disabled={isExploringDependency}
				title={"Compose and validate schema files"}
			>
				{!isValidating && <Layers />}
			</Button>
			<OptionsPopover
				title={"Compose options"}
				disabled={isValidating || isExploringDependency}
				options={composeOptions}
			/>
		</div>
	);
}

export function ComposeSection() {
	const files = useAppSelector(selectSourceFiles);

	if (files.length === 0) {
		return null;
	}

	return (
		<div className="px-2 pt-4 pb-2">
			<CliCommandDisplay type="compose" />
		</div>
	);
}
