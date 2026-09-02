import { getInsightDetailView } from "@insights-ui/components/insightDetailView";
import {
	closeInsightDetail,
	popInsightDetail,
	selectCanGoBackInsightDetail,
	selectInsightDetail,
} from "@insights-ui/state/insightDetailSlice";
import { DetailsPane } from "@/components/DetailsPane";
import { DetailsPaneShell } from "@/components/DetailsPaneShell";
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
			<DetailsPaneShell
				title={detailView.title}
				onClose={handleClose}
				onBack={canGoBack ? () => dispatch(popInsightDetail()) : undefined}
				bodyKey={detailView.key}
			>
				{detailView.content}
			</DetailsPaneShell>
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
