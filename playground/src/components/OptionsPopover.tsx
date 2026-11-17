import type { CheckedState } from "@radix-ui/react-checkbox";
import { Button } from "@shared-ui/components/button";
import { EllipsisVertical } from "lucide-react";
import { LabelCheckbox } from "@/components/ui/checkbox";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";

export type CheckboxOption = {
	id: string;
	label: string;
	/** The hover text of the option. */
	title?: string;
	checked: boolean;
	/** Whether this option alone is disabled. */
	disabled?: boolean;
	onCheckedChange: (checked: CheckedState) => void;
};

type OptionsPopoverProps = {
	/** The hover text of the options button. */
	title: string;
	/** Whether the options button and every option are disabled. */
	disabled: boolean;
	options: CheckboxOption[];
};

/**
 * An options button that opens a list of checkboxes above it. It sits to the
 * right of an action button and joins its border.
 */
export function OptionsPopover({
	title,
	disabled,
	options,
}: OptionsPopoverProps) {
	return (
		<Popover>
			<PopoverTrigger asChild={true}>
				<Button
					variant={"outline"}
					size={"icon-sm"}
					disabled={disabled}
					title={title}
					className={"rounded-l-none border-l-0"}
				>
					<EllipsisVertical className={"h-4 w-4"} />
				</Button>
			</PopoverTrigger>
			<PopoverContent side={"top"} align={"end"} className={"w-64 p-0"}>
				<ul className={"divide-y"}>
					{options.map((option) => {
						const isOptionDisabled = disabled || option.disabled === true;
						return (
							<li key={option.id} className={"px-4 py-3"} title={option.title}>
								<LabelCheckbox
									id={option.id}
									checked={option.checked}
									disabled={isOptionDisabled}
									onCheckedChange={option.onCheckedChange}
								>
									{option.label}
								</LabelCheckbox>
							</li>
						);
					})}
				</ul>
			</PopoverContent>
		</Popover>
	);
}
