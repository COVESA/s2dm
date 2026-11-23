import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { cn } from "@shared-ui/utils/cn";
import { CheckIcon, MinusIcon } from "lucide-react";
import { type ComponentProps, type ReactNode, useId } from "react";
import { FormLabel } from "@/components/ui/form-label";

/**
 * A checkbox. Its children follow the box in one row. Children that are not
 * a label leave the box without a name, so the box then needs an
 * `aria-label`. Without children, only the box is drawn.
 */
function Checkbox({
	className,
	children,
	...props
}: ComponentProps<typeof CheckboxPrimitive.Root>) {
	const box = (
		<CheckboxPrimitive.Root
			data-slot="checkbox"
			className={cn(
				"peer border-input dark:bg-input/30 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground dark:data-[state=checked]:bg-primary data-[state=checked]:border-primary data-[state=indeterminate]:bg-primary data-[state=indeterminate]:text-primary-foreground dark:data-[state=indeterminate]:bg-primary data-[state=indeterminate]:border-primary focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive size-4 shrink-0 cursor-pointer rounded-[4px] border shadow-xs transition-shadow outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50",
				className,
			)}
			{...props}
		>
			<CheckboxPrimitive.Indicator
				data-slot="checkbox-indicator"
				className="group grid place-content-center text-current transition-none"
			>
				<CheckIcon className="size-3.5 group-data-[state=indeterminate]:hidden" />
				<MinusIcon className="hidden size-3.5 group-data-[state=indeterminate]:block" />
			</CheckboxPrimitive.Indicator>
		</CheckboxPrimitive.Root>
	);

	if (children === undefined) {
		return box;
	}

	return (
		<div data-slot="checkbox-row" className="flex min-w-0 items-center gap-2">
			{box}
			{children}
		</div>
	);
}

type LabelCheckboxProps = Omit<
	ComponentProps<typeof CheckboxPrimitive.Root>,
	"children"
> & {
	/** The visible name of the box. */
	children: ReactNode;
	/** Whether the name shows the required mark. */
	showRequired?: boolean;
};

/**
 * A checkbox followed by its name. A click on the name toggles the box. The
 * name dims when the box is disabled.
 */
function LabelCheckbox({
	id,
	children,
	showRequired = false,
	...props
}: LabelCheckboxProps) {
	const generatedId = useId();
	const checkboxId = id ?? generatedId;

	return (
		<Checkbox id={checkboxId} {...props}>
			<FormLabel
				htmlFor={checkboxId}
				showRequired={showRequired}
				className="min-w-0 flex-1 cursor-pointer"
			>
				{children}
			</FormLabel>
		</Checkbox>
	);
}

export { Checkbox, LabelCheckbox };
