import { type ReactNode, useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

type HelpButtonProps = {
	title: string;
	ariaLabel: string;
	children: ReactNode;
};

export function HelpButton({ title, ariaLabel, children }: HelpButtonProps) {
	const [open, setOpen] = useState(false);

	return (
		<>
			<Button
				type="button"
				variant="outline"
				size="icon-xs"
				onClick={() => setOpen(true)}
				aria-label={ariaLabel}
				title="How this works"
			>
				?
			</Button>
			<Dialog open={open} onOpenChange={setOpen}>
				<DialogContent className="sm:max-w-2xl">
					<DialogHeader>
						<DialogTitle>{title}</DialogTitle>
					</DialogHeader>
					<ul className="mt-4 divide-y divide-border text-sm text-muted-foreground">
						{children}
					</ul>
				</DialogContent>
			</Dialog>
		</>
	);
}

type HelpItemProps = {
	term: ReactNode;
	children: ReactNode;
};

export function HelpItem({ term, children }: HelpItemProps) {
	return (
		<li className="grid grid-cols-[12rem_1fr] gap-x-4 py-3 first:pt-0 last:pb-0">
			<span className="font-medium text-foreground">{term}</span>
			<span>{children}</span>
		</li>
	);
}
