import type { ReactNode } from "react";
import { HighlightedText } from "@/components/explore/HighlightedText";
import {
	TreeDocsLink,
	TreeExpandSpacer,
	TreeRowFrame,
} from "@/components/explore/TreeRowParts";
import { Checkbox } from "@/components/ui/checkbox";
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

	let nameLabel: ReactNode = (
		<span
			className={"min-w-0 truncate font-mono text-sm text-foreground"}
			title={name}
		>
			<HighlightedText text={name} normalizedTerm={highlightTerm} />
		</span>
	);
	if (onShowDocs) {
		nameLabel = (
			<TreeDocsLink
				label={name}
				highlightTerm={highlightTerm}
				onClick={() => onShowDocs(name)}
			/>
		);
	}

	return (
		<TreeRowFrame depth={row.depth}>
			<TreeExpandSpacer />
			<Checkbox
				checked={isPicked}
				disabled={isDisabled}
				onCheckedChange={() => onToggle([name], !isPicked)}
				aria-label={`Select ${name}`}
			/>
			{nameLabel}
		</TreeRowFrame>
	);
}
