import { Button } from "@shared-ui/components/button";
import { cn } from "@shared-ui/utils/cn";
import { ChevronRight } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import { HighlightedText } from "@/components/explore/HighlightedText";
import { Checkbox } from "@/components/ui/checkbox";

export const TREE_ROW_HEIGHT_PX = 24;

const TREE_INDENT_REM = 1.25;

type TreeRowFrameProps = {
	depth: number;
	isMuted?: boolean;
	children: ReactNode;
};

export function TreeRowFrame({
	depth,
	isMuted = false,
	children,
}: TreeRowFrameProps) {
	const indent = `${depth * TREE_INDENT_REM}rem`;

	return (
		<div
			className={cn("flex h-6 items-center gap-1.5 bg-background", {
				"opacity-50": isMuted,
			})}
			style={{ paddingLeft: indent }}
		>
			{children}
		</div>
	);
}

type TreeExpandButtonProps = {
	isExpanded: boolean;
	isDisabled: boolean;
	onToggle: () => void;
};

export function TreeExpandButton({
	isExpanded,
	isDisabled,
	onToggle,
}: TreeExpandButtonProps) {
	let actionLabel = "Expand";
	if (isExpanded) {
		actionLabel = "Collapse";
	}

	return (
		<Button
			type={"button"}
			variant={"ghost"}
			size={"icon-sm"}
			className={"size-5"}
			onClick={onToggle}
			disabled={isDisabled}
			aria-label={actionLabel}
			aria-expanded={isExpanded}
		>
			<ChevronRight
				className={cn("size-4 transition-transform", {
					"rotate-90": isExpanded,
				})}
			/>
		</Button>
	);
}

export function TreeExpandSpacer() {
	return <span className={"size-5 shrink-0"} />;
}

type TreeDocsLinkProps = {
	label: string;
	highlightTerm: string;
	onClick: () => void;
};

export function TreeDocsLink({
	label,
	highlightTerm,
	onClick,
}: TreeDocsLinkProps) {
	return (
		<Button
			type={"button"}
			variant={"link"}
			className={
				"h-auto min-w-0 shrink justify-start p-0 font-mono font-normal text-foreground"
			}
			onClick={onClick}
			title={label}
		>
			<span className={"truncate"}>
				<HighlightedText text={label} normalizedTerm={highlightTerm} />
			</span>
		</Button>
	);
}

type DocsLinkCheckboxProps = Omit<
	ComponentProps<typeof Checkbox>,
	"aria-label" | "children"
> & {
	/** The name of the box and the text of its docs link. */
	label: string;
	highlightTerm: string;
	onShowDocs: () => void;
	/** Controls shown after the docs link. */
	children?: ReactNode;
};

/**
 * A checkbox followed by a docs link with the same name. A click on the link
 * opens the docs and leaves the box unchanged. Extra controls follow the link.
 */
export function DocsLinkCheckbox({
	label,
	highlightTerm,
	onShowDocs,
	children,
	...checkboxProps
}: DocsLinkCheckboxProps) {
	return (
		<Checkbox aria-label={`Select ${label}`} {...checkboxProps}>
			<TreeDocsLink
				label={label}
				highlightTerm={highlightTerm}
				onClick={onShowDocs}
			/>
			{children}
		</Checkbox>
	);
}
