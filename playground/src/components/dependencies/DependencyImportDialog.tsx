import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { FormLabel } from "@/components/ui/form-label";
import { Input } from "@/components/ui/input";

type DependencyImportDialogProps = {
	open: boolean;
	filename: string;
	configDirectory: string;
	error: string;
	onConfigDirectoryChange: (value: string) => void;
	onConfirm: () => void;
	onOpenChange: (open: boolean) => void;
};

export function DependencyImportDialog({
	open,
	filename,
	configDirectory,
	error,
	onConfigDirectoryChange,
	onConfirm,
	onOpenChange,
}: DependencyImportDialogProps) {
	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>Resolve Relative Selection Paths</DialogTitle>
					<DialogDescription>
						{filename} contains relative dependency selection paths. Enter the
						absolute parent directory of this config file so the backend can
						resolve them.
					</DialogDescription>
				</DialogHeader>
				<div className="grid gap-2 py-4">
					<FormLabel htmlFor="dependency-config-directory" showRequired>
						Config Directory
					</FormLabel>
					<Input
						id="dependency-config-directory"
						placeholder="/path/to/config-directory"
						value={configDirectory}
						onChange={(event) => onConfigDirectoryChange(event.target.value)}
						onKeyDown={(event) => {
							if (event.key === "Enter") {
								onConfirm();
							}
						}}
					/>
					{error && <p className="text-sm text-destructive">{error}</p>}
				</div>
				<DialogFooter>
					<Button variant="outline" onClick={() => onOpenChange(false)}>
						Cancel
					</Button>
					<Button onClick={onConfirm}>Import</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
