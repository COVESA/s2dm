import { Database, Plus, Trash2, Upload } from "lucide-react";
import { useState } from "react";
import { ConfirmActionDialog } from "@/components/ConfirmActionDialog";
import { FileListRow } from "@/components/FileListRow";
import { Button } from "@/components/ui/button";
import { ImportErrorBanner } from "@/components/ui/import-error-banner";
import { Dropdown, DropdownItem } from "@/components/ui/simple-dropdown";
import { useFileImport } from "@/hooks/useFileImport";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	closeLedger,
	openLedger,
	selectLedgerError,
	selectLedgerFileName,
} from "@/store/ledger/ledgerSlice";

type LedgerFileListProps = {
	leading?: React.ReactNode;
};

export function LedgerFileList({ leading }: LedgerFileListProps) {
	const dispatch = useAppDispatch();
	const fileName = useAppSelector(selectLedgerFileName);
	const error = useAppSelector(selectLedgerError);
	const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);

	const { openImportInput, hiddenInputProps } = useFileImport({
		accept: ".db,.sqlite,.sqlite3",
		onFilesSelected: (files) => {
			const file = files[0];
			if (file) {
				dispatch(openLedger(file));
			}
		},
	});

	return (
		<div className="flex flex-col">
			<div className="flex items-center justify-between gap-2 p-2">
				<div className="flex items-center gap-2">{leading}</div>
				<div className="flex items-center gap-2">
					<Dropdown
						trigger={
							<Button variant="outline" size="icon" title="Add ledger">
								<Plus className="h-5 w-5" />
							</Button>
						}
						align="end"
					>
						<DropdownItem onClick={openImportInput}>
							<Upload className="h-4 w-4" />
							Upload Ledger
						</DropdownItem>
					</Dropdown>
					<Button
						variant="outline"
						size="icon"
						onClick={() => setShowRemoveConfirm(true)}
						disabled={!fileName}
						title="Remove ledger"
						className="text-destructive hover:text-destructive hover:bg-destructive/10"
					>
						<Trash2 className="h-5 w-5" />
					</Button>
				</div>
			</div>

			<input {...hiddenInputProps} />

			{error && <ImportErrorBanner>{error}</ImportErrorBanner>}

			{fileName && (
				<div className="px-2 pt-2">
					<ul className="space-y-1 py-2">
						<FileListRow
							// A placeholder where the schema list has its drag handle, so
							// the name lines up across the two sidebars. One ledger cannot
							// be reordered, so there is nothing to grab.
							leading={<span className="h-8 w-4" />}
							icon={<Database className="h-4 w-4 flex-shrink-0" />}
							label={fileName}
							title={fileName}
						/>
					</ul>
				</div>
			)}

			<ConfirmActionDialog
				open={showRemoveConfirm}
				onOpenChange={setShowRemoveConfirm}
				title="Remove ledger?"
				description={
					<>
						This will close {fileName} and clear its tables, searches and
						queries. This action cannot be undone.
					</>
				}
				confirmLabel="Remove Ledger"
				onConfirm={() => {
					setShowRemoveConfirm(false);
					dispatch(closeLedger());
				}}
			/>
		</div>
	);
}
