import { LedgerDetailsContent } from "@ledger-ui/components/LedgerDetailsContent";
import {
	closeLedgerDetail,
	selectHasLedger,
} from "@ledger-ui/state/ledgerSlice";
import { DetailsPane } from "@/components/DetailsPane";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { collapseResultPane } from "@/store/ui/uiSlice";

type LedgerDetailsPaneProps = {
	position?: "none" | "left" | "center" | "right";
	collapsible?: boolean;
	className?: string;
};

export function LedgerDetailsPane({
	position = "right",
	collapsible,
	className,
}: LedgerDetailsPaneProps) {
	const dispatch = useAppDispatch();
	const hasLedger = useAppSelector(selectHasLedger);

	const handleClose = () => {
		dispatch(closeLedgerDetail());
		dispatch(collapseResultPane());
	};

	return (
		<DetailsPane
			className={className}
			position={position}
			collapsible={collapsible}
			hasContent={hasLedger}
		>
			<LedgerDetailsContent onClose={handleClose} />
		</DetailsPane>
	);
}
