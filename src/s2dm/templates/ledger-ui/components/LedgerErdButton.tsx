import { LedgerErdDiagram } from "@ledger-ui/components/LedgerErdDiagram";
import { Network } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

export function LedgerErdButton() {
	const [open, setOpen] = useState(false);

	return (
		<>
			<Button
				variant="outline"
				size="sm"
				className="w-full"
				onClick={() => setOpen(true)}
			>
				<Network className="h-4 w-4" />
				View relationships
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
