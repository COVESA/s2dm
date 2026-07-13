import { Layers } from "lucide-react";
import { CliCommandDisplay } from "@/components/CliCommandDisplay";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { FormLabel } from "@/components/ui/form-label";
import { selectHasComposedDependenciesSchema } from "@/store/deps/compose/composeSlice";
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
import { cn } from "@/utils/cn";

export function ComposeSection() {
	const dispatch = useAppDispatch();
	const files = useAppSelector(selectSourceFiles);
	const hasBuiltDependenciesSchema = useAppSelector(
		selectHasComposedDependenciesSchema,
	);
	const includeBuiltDependencies = useAppSelector(
		selectIncludeBuiltDependencies,
	);
	const isValidating = useAppSelector(selectIsValidating);

	const handleCompose = () => {
		dispatch(validateAndCompose());
	};

	if (files.length === 0) {
		return null;
	}

	const includeBuiltDependenciesTooltip = hasBuiltDependenciesSchema
		? undefined
		: "Build dependencies in the Dependencies tab before including them in composition.";

	let buttonContent: React.ReactNode;
	if (isValidating) {
		buttonContent = "Validating...";
	} else {
		buttonContent = (
			<>
				<Layers />
				Compose and Validate
			</>
		);
	}

	return (
		<>
			<div className="px-2 pt-2">
				<div className="mb-2 flex items-center justify-between gap-3">
					<div
						className="flex items-center space-x-2"
						title={includeBuiltDependenciesTooltip}
					>
						<Checkbox
							id="include-built-dependencies"
							checked={includeBuiltDependencies}
							disabled={!hasBuiltDependenciesSchema || isValidating}
							onCheckedChange={(checked) => {
								const nextValue = checked === true;
								dispatch(setIncludeBuiltDependencies(nextValue));
							}}
						/>
						<FormLabel
							htmlFor="include-built-dependencies"
							className={cn(
								"text-sm",
								!hasBuiltDependenciesSchema && "text-muted-foreground",
							)}
						>
							<span className="cursor-pointer">
								Include built dependencies in composition
							</span>
						</FormLabel>
					</div>
				</div>
				<Button
					variant="outline"
					size="sm"
					className="w-full"
					onClick={handleCompose}
					loading={isValidating}
					title="Compose and validate schema files"
				>
					{buttonContent}
				</Button>
			</div>
			<div className="px-2 pt-4 pb-2">
				<CliCommandDisplay type="compose" />
			</div>
		</>
	);
}
