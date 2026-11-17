import {
	closeLedger,
	selectLedgerError,
	selectLedgerFileName,
} from "@ledger-ui/state/ledgerSlice";
import { Button } from "@shared-ui/components/button";
import { StatusBanner } from "@shared-ui/components/status-banner";
import { Database, Trash2 } from "lucide-react";
import { useConfirmPrompt } from "@/components/ConfirmPromptProvider";
import { FileListRow } from "@/components/FileListRow";
import { LedgerErdButton } from "@/components/ledger/LedgerErdButton";
import { useAppDispatch, useAppSelector } from "@/store/hooks";

const REMOVE_LABEL = "Remove ledger";

export function LedgerFileList() {
	const dispatch = useAppDispatch();
	const fileName = useAppSelector(selectLedgerFileName);
	const error = useAppSelector(selectLedgerError);
	const confirmAction = useConfirmPrompt();

	const handleRemoveLedger = () => {
		confirmAction({
			title: "Remove ledger?",
			description: `This will close ${fileName} and clear its tables, searches and queries. This action cannot be undone.`,
			confirmLabel: "Remove Ledger",
			onConfirm: () => {
				const closeAction = closeLedger();
				dispatch(closeAction);
			},
		});
	};

	return (
		<div className="flex flex-col">
			{error && (
				<StatusBanner variant={"destructive"} className={"mx-2 mb-2"}>
					{error}
				</StatusBanner>
			)}

			{fileName && (
				<div className="px-2 pt-2">
					<ul className="space-y-1 py-2">
						<FileListRow
							icon={<Database className="h-4 w-4 flex-shrink-0" />}
							label={fileName}
							title={fileName}
							trailing={
								<>
									<LedgerErdButton />
									<Button
										type={"button"}
										variant={"ghost"}
										size={"icon-sm"}
										className={
											"text-destructive hover:bg-destructive/10 hover:text-destructive"
										}
										onClick={handleRemoveLedger}
										aria-label={REMOVE_LABEL}
										title={REMOVE_LABEL}
									>
										<Trash2 />
									</Button>
								</>
							}
						/>
					</ul>
				</div>
			)}
		</div>
	);
}
