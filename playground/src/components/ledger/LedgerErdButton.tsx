import { LedgerErdDiagram } from "@ledger-ui/components/LedgerErdDiagram";
import { Button } from "@shared-ui/components/button";
import { Network } from "lucide-react";
import { useState } from "react";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

const BUTTON_LABEL = "View relationships";

/**
 * An icon button that opens the ledger relationships diagram in a dialog.
 */
export function LedgerErdButton() {
	const [open, setOpen] = useState(false);

	return (
		<>
			<Button
				type={"button"}
				variant={"ghost"}
				size={"icon-sm"}
				className={"hover:bg-background/70"}
				onClick={() => setOpen(true)}
				aria-label={BUTTON_LABEL}
				title={BUTTON_LABEL}
			>
				<Network />
			</Button>

			<Dialog open={open} onOpenChange={setOpen}>
				<DialogContent className="flex h-[90vh] w-[90vw] max-w-none flex-col p-0 sm:max-w-none">
					<DialogHeader className="shrink-0 border-b px-6 py-4">
						<DialogTitle>Ledger relationships</DialogTitle>
					</DialogHeader>
					<LedgerErdDiagram active={open} className="flex-1 overflow-hidden" />
				</DialogContent>
			</Dialog>
		</>
	);
}
