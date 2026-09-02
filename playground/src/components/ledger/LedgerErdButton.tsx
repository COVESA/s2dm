import { Network } from "lucide-react";
import { useEffect, useState } from "react";
import { LedgerErrorBanner } from "@/components/ledger/LedgerErrorBanner";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { useTheme } from "@/hooks/useTheme";
import { LEDGER_ER_DIAGRAM } from "@/ledger/erDiagram";

export function LedgerErdButton() {
	const theme = useTheme();
	const [open, setOpen] = useState(false);
	const [isDrawn, setIsDrawn] = useState(false);
	const [error, setError] = useState<string | null>(null);
	// Held as state, not a ref: Radix mounts the dialog body in a later commit
	// than the one that opens it, so an effect keyed on `open` alone sees no node.
	const [host, setHost] = useState<HTMLDivElement | null>(null);

	useEffect(() => {
		if (!open || !host) {
			return;
		}

		let cancelled = false;
		setIsDrawn(false);
		setError(null);

		// Loaded on demand: mermaid is larger than the rest of the workspace.
		import("mermaid")
			.then(async ({ default: mermaid }) => {
				if (cancelled) {
					return;
				}
				mermaid.initialize({
					startOnLoad: false,
					securityLevel: "strict",
					theme: theme === "dark" ? "dark" : "default",
				});
				// mermaid replaces the node's text with the drawing, so the source is
				// assigned as text and never as markup.
				host.textContent = LEDGER_ER_DIAGRAM;
				host.removeAttribute("data-processed");
				await mermaid.run({ nodes: [host] });
				if (!cancelled) {
					setIsDrawn(true);
				}
			})
			.catch((reason: unknown) => {
				if (!cancelled) {
					setError(reason instanceof Error ? reason.message : String(reason));
				}
			});

		return () => {
			cancelled = true;
		};
	}, [open, host, theme]);

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
					<div className="relative flex-1 overflow-hidden">
						<div
							ref={setHost}
							className="flex h-full w-full items-start justify-center overflow-auto p-6 [&_svg]:max-w-none"
						/>
						{!isDrawn && !error && (
							<div className="absolute inset-0 bg-background">
								<EmptyState isLoading title="Drawing diagram..." />
							</div>
						)}
						{error && (
							<div className="absolute inset-0 bg-background p-6">
								<LedgerErrorBanner>{error}</LedgerErrorBanner>
							</div>
						)}
					</div>
				</DialogContent>
			</Dialog>
		</>
	);
}
