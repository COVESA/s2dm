import { readFileBytes } from "@ledger-ui/data/sqlite";
import {
	openLedger,
	openLedgerFailure,
	selectIsLoadingLedger,
} from "@ledger-ui/state/ledgerSlice";
import { Button } from "@shared-ui/components/button";
import { Upload } from "lucide-react";
import { useRef } from "react";
import { LedgerHelpButton } from "@/components/ledger/LedgerHelpButton";
import { useFileImport } from "@/hooks/useFileImport";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { getErrorMessage } from "@/utils/getErrorMessage";

export function LedgerActions() {
	const dispatch = useAppDispatch();
	const isLoading = useAppSelector(selectIsLoadingLedger);
	// The read happens before the action is dispatched, so ordering and failure
	// are this component's to handle rather than the saga's.
	const latestImport = useRef(0);

	const { openImportInput, hiddenInputProps } = useFileImport({
		accept: ".db,.sqlite,.sqlite3",
		onFilesSelected: (files) => {
			const file = files[0];
			if (!file) {
				return;
			}
			const sequence = latestImport.current + 1;
			latestImport.current = sequence;
			readFileBytes(file)
				.then((bytes) => {
					// A newer pick already superseded this read.
					if (sequence === latestImport.current) {
						dispatch(openLedger({ name: file.name, bytes }));
					}
				})
				.catch((error: unknown) => {
					// Guarded like the success path: a superseded read must not
					// report over the ledger that did open.
					if (sequence !== latestImport.current) {
						return;
					}
					const message = getErrorMessage(error);
					dispatch(openLedgerFailure({ message }));
				});
		},
	});

	return (
		<>
			<div className="flex items-center gap-2">
				<LedgerHelpButton />
				<Button
					variant={"outline"}
					size={"icon"}
					onClick={openImportInput}
					title={"Upload ledger"}
					loading={isLoading}
				>
					{!isLoading && <Upload className={"h-5 w-5"} />}
				</Button>
			</div>

			<input {...hiddenInputProps} />
		</>
	);
}
