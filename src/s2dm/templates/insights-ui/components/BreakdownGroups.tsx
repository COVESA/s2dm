import { EvidenceList } from "@insights-ui/components/EvidenceList";
import { MiniStackedBar } from "@insights-ui/components/MiniStackedBar";
import type { BreakdownGroup } from "@insights-ui/selectors/concepts";
import { cn } from "@shared-ui/utils/cn";

const COLUMN_CLASS: Record<number, string> = {
	1: "md:grid-cols-1",
	2: "md:grid-cols-2",
	3: "md:grid-cols-3",
};

export function BreakdownGroups({ groups }: { groups: BreakdownGroup[] }) {
	const columnClass =
		COLUMN_CLASS[Math.min(groups.length, 3)] ?? "md:grid-cols-3";

	return (
		<div className={cn("grid grid-cols-1 gap-8", columnClass)}>
			{groups.map((group, index) => (
				<div
					key={group.title}
					className={cn(
						"flex flex-col gap-3",
						index > 0 && "md:border-l md:border-border md:pl-8",
					)}
				>
					<div>
						<div className="text-base font-semibold text-card-foreground">
							{group.title}
						</div>
						<div className="text-sm text-muted-foreground">
							Total:{" "}
							<span className="font-semibold text-card-foreground">
								{group.total}
							</span>
						</div>
					</div>
					{group.segments && <MiniStackedBar segments={group.segments} />}
					<EvidenceList className="gap-1 text-sm">
						{group.segments?.map((segment) => (
							<li key={segment.label} className="flex items-center gap-2">
								<span
									className={cn(
										"h-2.5 w-2.5 shrink-0 rounded-sm",
										segment.colorClassName,
									)}
								/>
								<span className="text-muted-foreground">{segment.label}:</span>
								<span className="font-semibold text-card-foreground">
									{segment.value}
								</span>
							</li>
						))}
						{group.stats?.map((stat) => (
							<li key={stat.label} className="flex items-center gap-2">
								<span className="text-muted-foreground">{stat.label}:</span>
								<span className="font-semibold text-card-foreground">
									{stat.value}
								</span>
							</li>
						))}
					</EvidenceList>
				</div>
			))}
		</div>
	);
}
