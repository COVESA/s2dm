import { InstancePickContent } from "@/components/explore/instancePick/InstancePickContent";
import { InstancePickTrigger } from "@/components/explore/instancePick/InstancePickTrigger";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";

export type InstancePickPopoverProps = {
	title: string;
	names: string[];
	pickedNames: Set<string>;
	isDisabled: boolean;
	onToggle: (toggledNames: string[], isChecked: boolean) => void;
};

export function InstancePickPopover({
	title,
	names,
	pickedNames,
	isDisabled,
	onToggle,
}: InstancePickPopoverProps) {
	const pickedCount = names.filter((name) => pickedNames.has(name)).length;

	return (
		<Popover>
			<PopoverTrigger asChild={true}>
				<InstancePickTrigger
					label={title}
					pickedCount={pickedCount}
					totalCount={names.length}
					isDisabled={isDisabled}
				/>
			</PopoverTrigger>
			<PopoverContent side={"right"} align={"start"} className={"w-56 p-0"}>
				<InstancePickContent
					title={title}
					names={names}
					pickedNames={pickedNames}
					pickedCount={pickedCount}
					isDisabled={isDisabled}
					onToggle={onToggle}
				/>
			</PopoverContent>
		</Popover>
	);
}
