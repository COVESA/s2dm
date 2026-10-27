import { cn } from "@shared-ui/utils/cn";

const SPECTRUM_GRADIENT =
	"linear-gradient(to right, hsl(0, 80%, 45%) 0%, hsl(30, 80%, 45%) 25%, hsl(60, 80%, 45%) 50%, hsl(90, 80%, 45%) 75%, hsl(120, 80%, 45%) 100%)";

type DocumentationCoverageBarProps = {
	label: string;
	documented: number;
	total: number;
};

export function DocumentationCoverageBar({
	label,
	documented,
	total,
}: DocumentationCoverageBarProps) {
	const rawPercent = total === 0 ? 0 : (documented / total) * 100;

	let percentLabel: string;
	if (documented === 0) {
		percentLabel = "0%";
	} else if (rawPercent < 1) {
		percentLabel = "< 1%";
	} else {
		percentLabel = `${Math.round(rawPercent)}%`;
	}

	let fillBackgroundSize = "100% 100%";
	if (rawPercent > 0) {
		fillBackgroundSize = `${(100 / rawPercent) * 100}% 100%`;
	}

	return (
		<div className="flex items-center gap-3">
			<span
				className={cn(
					"w-32 shrink-0 text-sm",
					total > 0 && documented === 0
						? "text-destructive"
						: "text-muted-foreground",
				)}
			>
				{label}
			</span>
			<div className="h-4 flex-1 rounded-full bg-muted">
				<div
					className={cn("h-full rounded-full", documented > 0 && "min-w-4")}
					style={{
						width: `${rawPercent}%`,
						backgroundImage: SPECTRUM_GRADIENT,
						backgroundSize: fillBackgroundSize,
					}}
				/>
			</div>
			<span
				className="w-10 cursor-help text-right text-sm text-muted-foreground"
				title={`${documented}/${total} documented`}
			>
				{percentLabel}
			</span>
		</div>
	);
}
