import { Folder, Link, Package, Plus, Trash2, Upload } from "lucide-react";
import { useState } from "react";
import { AddUrlDialog } from "@/components/AddUrlDialog";
import { ConfirmActionDialog } from "@/components/ConfirmActionDialog";
import { DependencyManagerDialog } from "@/components/DependencyManagerDialog";
import { Button } from "@/components/ui/button";
import { Dropdown, DropdownItem } from "@/components/ui/simple-dropdown";
import { useImportSources } from "@/hooks/useImportSources";
import { selectExploringDependencyId } from "@/store/deps/dependencyExploration/dependencyExplorationSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectSourceFiles, setSourceFiles } from "@/store/schema/schemaSlice";

export function FileListHeader() {
	const dispatch = useAppDispatch();
	const files = useAppSelector(selectSourceFiles);
	const exploringDependencyId = useAppSelector(selectExploringDependencyId);
	const isExploring = Boolean(exploringDependencyId);

	const {
		openFileImport,
		openFolderImport,
		addUrl,
		error: importError,
		hiddenInputs,
	} = useImportSources();

	const [showClearConfirm, setShowClearConfirm] = useState(false);
	const [showDependenciesDialog, setShowDependenciesDialog] = useState(false);
	const [showUrlDialog, setShowUrlDialog] = useState(false);

	const confirmClearAll = () => {
		setShowClearConfirm(false);
		dispatch(setSourceFiles([]));
	};

	return (
		<>
			<div className="flex justify-end gap-2 p-2">
				<Button
					variant="outline"
					size="icon"
					onClick={() => setShowDependenciesDialog(true)}
					disabled={isExploring}
					title="Manage dependencies"
				>
					<Package className="h-5 w-5" />
				</Button>
				<Dropdown
					trigger={
						<Button variant="outline" size="icon" title="Add schemas">
							<Plus className="h-5 w-5" />
						</Button>
					}
					align="end"
				>
					<DropdownItem onClick={openFileImport}>
						<Upload className="h-4 w-4" />
						Upload Files
					</DropdownItem>
					<DropdownItem onClick={openFolderImport}>
						<Folder className="h-4 w-4" />
						Upload Directory
					</DropdownItem>
					<DropdownItem onClick={() => setShowUrlDialog(true)}>
						<Link className="h-4 w-4" />
						Add URL
					</DropdownItem>
				</Dropdown>
				<Button
					variant="outline"
					size="icon"
					onClick={() => setShowClearConfirm(true)}
					disabled={files.length === 0}
					title="Remove all files"
					className="text-destructive hover:text-destructive hover:bg-destructive/10"
				>
					<Trash2 className="h-5 w-5" />
				</Button>
			</div>

			{importError && (
				<div className="mx-2 mb-2 p-2 text-sm bg-destructive/10 text-destructive rounded border border-destructive">
					{importError}
				</div>
			)}

			{hiddenInputs}

			<ConfirmActionDialog
				open={showClearConfirm}
				onOpenChange={setShowClearConfirm}
				title="Remove all files?"
				description={
					<>
						This will remove all {files.length} file
						{files.length !== 1 ? "s" : ""} from the list. This action cannot be
						undone.
					</>
				}
				confirmLabel="Remove All"
				onConfirm={confirmClearAll}
			/>

			<AddUrlDialog
				open={showUrlDialog}
				onOpenChange={setShowUrlDialog}
				onAdd={addUrl}
			/>

			<DependencyManagerDialog
				open={showDependenciesDialog}
				onOpenChange={setShowDependenciesDialog}
			/>
		</>
	);
}
