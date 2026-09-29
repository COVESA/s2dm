import { ArrowLeft, X } from "lucide-react";

type DetailsPaneShellProps = {
	title: string;
	onClose: () => void;
	onBack?: () => void;
	trailing?: React.ReactNode;
	// Changing it replays the slide-in, so navigating between details animates.
	bodyKey?: string;
	children: React.ReactNode;
};

export function DetailsPaneShell({
	title,
	onClose,
	onBack,
	trailing,
	bodyKey,
	children,
}: DetailsPaneShellProps) {
	return (
		<div className="flex h-full flex-col">
			<div className="flex items-center justify-between gap-2 border-b px-5 py-4">
				<div className="flex min-w-0 items-center gap-2">
					{onBack && (
						<button
							type="button"
							onClick={onBack}
							className="shrink-0 cursor-pointer rounded-md p-1 text-muted-foreground hover:bg-muted"
							aria-label="Back"
						>
							<ArrowLeft className="h-4 w-4" />
						</button>
					)}
					<span
						className="truncate text-lg font-semibold text-card-foreground"
						title={title}
					>
						{title}
					</span>
				</div>
				<div className="flex shrink-0 items-center gap-2">
					{trailing}
					<button
						type="button"
						onClick={onClose}
						className="shrink-0 cursor-pointer rounded-md p-1 text-muted-foreground hover:bg-muted"
						aria-label="Close details"
					>
						<X className="h-4 w-4" />
					</button>
				</div>
			</div>
			<div
				key={bodyKey}
				className="flex-1 animate-in overflow-y-auto px-5 pt-5 pb-14 fade-in slide-in-from-right-4 duration-200"
			>
				{children}
			</div>
		</div>
	);
}
