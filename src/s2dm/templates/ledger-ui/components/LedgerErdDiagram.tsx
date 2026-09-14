import { LedgerErrorBanner } from "@ledger-ui/components/LedgerErrorBanner";
import { LEDGER_ER_DIAGRAM } from "@ledger-ui/data/erDiagram";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { useTheme } from "@/hooks/useTheme";

type LedgerErdDiagramProps = {
	// False while a host has the diagram hidden, so mermaid is not asked to draw
	// into a node with no size.
	active?: boolean;
	className?: string;
	// Scales the drawing to the width it is given. A dialog wants the opposite:
	// its own scroll, at whatever size mermaid chose.
	fit?: boolean;
};

export function LedgerErdDiagram({
	active = true,
	className,
	fit = false,
}: LedgerErdDiagramProps) {
	const theme = useTheme();
	const [isDrawn, setIsDrawn] = useState(false);
	const [error, setError] = useState<string | null>(null);
	// Held as state, not a ref: Radix mounts the dialog body in a later commit
	// than the one that opens it, so an effect keyed on the flag alone sees no node.
	const [host, setHost] = useState<HTMLDivElement | null>(null);

	useEffect(() => {
		if (!active || !host) {
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
	}, [active, host, theme]);

	return (
		<div className={`relative ${className ?? ""}`}>
			<div
				ref={setHost}
				className={
					fit
						? "flex w-full items-start justify-center [&_svg]:h-auto [&_svg]:w-full"
						: "flex h-full w-full items-start justify-center overflow-auto p-6 [&_svg]:max-w-none"
				}
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
	);
}
