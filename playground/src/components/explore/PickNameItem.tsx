import type { ReactNode } from "react";
import { HighlightedText } from "@/components/explore/HighlightedText";
import {
	DocsLinkCheckbox,
	TreeExpandSpacer,
	TreeRowFrame,
} from "@/components/explore/TreeRowParts";
import { LabelCheckbox } from "@/components/ui/checkbox";
import type { PickNameTreeRow } from "@/utils/selectionQuery/treeRows";

type PickNameItemProps = {
	row: PickNameTreeRow;
	isPicked: boolean;
	isDisabled: boolean;
	onToggle: (names: string[], isChecked: boolean) => void;
	onShowDocs?: (name: string) => void;
};

export function PickNameItem({
	row,
	isPicked,
	isDisabled,
	onToggle,
	onShowDocs,
}: PickNameItemProps) {
	const { name, highlightTerm } = row;

	const handleCheckedChange = () => onToggle([name], !isPicked);

	let nameCheckbox: ReactNode = (
		<LabelCheckbox
			checked={isPicked}
			disabled={isDisabled}
			onCheckedChange={handleCheckedChange}
		>
			<span className={"truncate font-mono font-normal"} title={name}>
				<HighlightedText text={name} normalizedTerm={highlightTerm} />
			</span>
		</LabelCheckbox>
	);
	if (onShowDocs) {
		nameCheckbox = (
			<DocsLinkCheckbox
				label={name}
				highlightTerm={highlightTerm}
				onShowDocs={() => onShowDocs(name)}
				checked={isPicked}
				disabled={isDisabled}
				onCheckedChange={handleCheckedChange}
			/>
		);
	}

	return (
		<TreeRowFrame depth={row.depth}>
			<TreeExpandSpacer />
			{nameCheckbox}
		</TreeRowFrame>
	);
}
