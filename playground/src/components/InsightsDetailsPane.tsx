import { getInsightDetailView } from "@insights-ui/components/insightDetailView";
import {
	closeInsightDetail,
	popInsightDetail,
	selectCanGoBackInsightDetail,
	selectInsightDetail,
} from "@insights-ui/state/insightDetailSlice";
import { ArrowLeft, X } from "lucide-react";
import { DetailsPane } from "@/components/DetailsPane";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectFilteredSchema } from "@/store/schema/schemaSlice";
import { collapseResultPane } from "@/store/ui/uiSlice";

type InsightsDetailsPaneProps = {
	position?: "none" | "left" | "center" | "right";
	collapsible?: boolean;
	className?: string;
};

export function InsightsDetailsPane({
	position = "right",
	collapsible,
	className,
}: InsightsDetailsPaneProps) {
	const dispatch = useAppDispatch();
	const detail = useAppSelector(selectInsightDetail);
	const canGoBack = useAppSelector(selectCanGoBackInsightDetail);
	const filteredSchema = useAppSelector(selectFilteredSchema);
	const hasFilteredSchema = filteredSchema.trim().length > 0;
	const detailView = detail ? getInsightDetailView(detail) : null;

	const handleClose = () => {
		dispatch(closeInsightDetail());
		dispatch(collapseResultPane());
	};

	let content: React.ReactNode;
	if (!detailView) {
		content = (
			<div className="flex flex-1 items-center justify-center p-5 text-center text-muted-foreground">
				<p>Select a card to see details</p>
			</div>
		);
	} else {
		content = (
			<div className="flex h-full flex-col">
				<div className="flex items-center justify-between border-b px-5 py-4">
					<div className="flex min-w-0 items-center gap-2">
						{canGoBack && (
							<button
								type="button"
								onClick={() => dispatch(popInsightDetail())}
								className="shrink-0 cursor-pointer rounded-md p-1 text-muted-foreground hover:bg-muted"
								aria-label="Back"
							>
								<ArrowLeft className="h-4 w-4" />
							</button>
						)}
						<span className="truncate text-lg font-semibold text-card-foreground">
							{detailView.title}
						</span>
					</div>
					<button
						type="button"
						onClick={handleClose}
						className="shrink-0 cursor-pointer rounded-md p-1 text-muted-foreground hover:bg-muted"
						aria-label="Close details"
					>
						<X className="h-4 w-4" />
					</button>
				</div>
				<div
					key={detailView.key}
					className="flex-1 animate-in overflow-y-auto px-5 pt-5 pb-14 fade-in slide-in-from-right-4 duration-200"
				>
					{detailView.content}
				</div>
			</div>
		);
	}

	return (
		<DetailsPane
			className={className}
			position={position}
			collapsible={collapsible}
			hasContent={hasFilteredSchema}
		>
			{content}
		</DetailsPane>
	);
}
