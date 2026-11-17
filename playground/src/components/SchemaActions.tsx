import { Button } from "@shared-ui/components/button";
import { Folder, Link, Package, Plus, Upload } from "lucide-react";
import { useState } from "react";
import { AddUrlDialog } from "@/components/AddUrlDialog";
import { DependencyManagerDialog } from "@/components/DependencyManagerDialog";
import { SchemaHelpButton } from "@/components/SchemaHelpButton";
import { Dropdown, DropdownItem } from "@/components/ui/simple-dropdown";
import { useImportSources } from "@/hooks/useImportSources";
import { selectExploringDependencyId } from "@/store/exploration/explorationSlice";
import { useAppSelector } from "@/store/hooks";

export function SchemaActions() {
	const exploringDependencyId = useAppSelector(selectExploringDependencyId);
	const isExploring = Boolean(exploringDependencyId);

	const { openFileImport, openFolderImport, addUrl, hiddenInputs } =
		useImportSources();

	const [showDependenciesDialog, setShowDependenciesDialog] = useState(false);
	const [showUrlDialog, setShowUrlDialog] = useState(false);

	return (
		<>
			<div className="flex items-center gap-2">
				<SchemaHelpButton />
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
			</div>

			{hiddenInputs}

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
