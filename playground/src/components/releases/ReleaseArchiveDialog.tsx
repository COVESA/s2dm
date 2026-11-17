import { Button } from "@shared-ui/components/button";
import { StatusBanner } from "@shared-ui/components/status-banner";
import { FileArchive } from "lucide-react";
import { useState } from "react";
import type { ReleaseAsset } from "@/api/types";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { formatAssetSize } from "@/utils/releaseAssets";

type ReleaseArchiveDialogProps = {
	choices: ReleaseAsset[] | null;
	isOpening: boolean;
	error: string | null;
	onPick: (archiveName: string) => void;
	onCancel: () => void;
};

export function ReleaseArchiveDialog({
	choices,
	isOpening,
	error,
	onPick,
	onCancel,
}: ReleaseArchiveDialogProps) {
	const [pickedArchiveName, setPickedArchiveName] = useState<string | null>(
		null,
	);

	const handlePick = (archiveName: string) => {
		setPickedArchiveName(archiveName);
		onPick(archiveName);
	};

	const handleOpenChange = (open: boolean) => {
		if (!open) {
			onCancel();
		}
	};

	return (
		<Dialog open={choices !== null} onOpenChange={handleOpenChange}>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>Choose an Archive</DialogTitle>
					<DialogDescription>
						Select the release asset to open.
					</DialogDescription>
				</DialogHeader>
				<ul className={"grid gap-2 py-4"}>
					{choices?.map((archive) => {
						const sizeText = formatAssetSize(archive.size);
						return (
							<li key={archive.name}>
								<Button
									type={"button"}
									variant={"outline"}
									className={"w-full justify-start"}
									disabled={isOpening}
									loading={isOpening && archive.name === pickedArchiveName}
									onClick={() => handlePick(archive.name)}
								>
									<FileArchive />
									<span className={"truncate"}>{archive.name}</span>
									<span
										className={"ml-auto shrink-0 text-xs text-muted-foreground"}
									>
										{sizeText}
									</span>
								</Button>
							</li>
						);
					})}
				</ul>
				{error !== null && (
					<StatusBanner variant={"destructive"}>{error}</StatusBanner>
				)}
				<DialogFooter>
					<Button type={"button"} variant={"outline"} onClick={onCancel}>
						Cancel
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
