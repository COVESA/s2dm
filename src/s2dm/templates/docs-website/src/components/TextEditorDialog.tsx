import type { ReactNode } from "react";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

type TextEditorDialogProps = {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	title: string;
	children: ReactNode;
};

export function TextEditorDialog({
	open,
	onOpenChange,
	title,
	children,
}: TextEditorDialogProps) {
	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="h-[90vh] w-[90vw] max-w-none flex flex-col p-0 sm:max-w-none">
				<DialogHeader className="shrink-0 border-b px-6 py-4">
					<DialogTitle>{title}</DialogTitle>
				</DialogHeader>
				<div className="flex-1 overflow-hidden">{children}</div>
			</DialogContent>
		</Dialog>
	);
}
