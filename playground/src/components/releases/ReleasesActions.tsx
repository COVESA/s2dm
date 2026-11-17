import { Button } from "@shared-ui/components/button";
import { KeyRound, Trash2 } from "lucide-react";
import { useState } from "react";
import { useConfirmPrompt } from "@/components/ConfirmPromptProvider";
import { IdentitiesManagerDialog } from "@/components/IdentitiesManagerDialog";
import { ReleasesHelpButton } from "@/components/releases/ReleasesHelpButton";
import {
	exitExploration,
	selectExploringReleaseId,
} from "@/store/exploration/explorationSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	clearRepository,
	selectReleases,
} from "@/store/releases/releasesSlice";

export function ReleasesActions() {
	const dispatch = useAppDispatch();
	const releases = useAppSelector(selectReleases);
	const exploringReleaseId = useAppSelector(selectExploringReleaseId);
	const confirmAction = useConfirmPrompt();
	const [showIdentitiesDialog, setShowIdentitiesDialog] = useState(false);

	const isExploringRelease = exploringReleaseId !== null;
	const hasRepository = releases.repository !== "";
	const isBusy = releases.isLoadingPage || releases.openingTag !== null;

	let removeDescription = "This will clear the loaded releases.";
	if (isExploringRelease) {
		removeDescription =
			"This will clear the loaded releases. Exploring stops, and unsaved selection query changes are discarded.";
	}

	const removeRepository = () => {
		if (isExploringRelease) {
			const exitAction = exitExploration();
			dispatch(exitAction);
		}
		const clearAction = clearRepository();
		dispatch(clearAction);
	};

	const handleRemoveRepository = () => {
		confirmAction({
			title: "Remove repository?",
			description: removeDescription,
			confirmLabel: "Remove Repository",
			onConfirm: removeRepository,
		});
	};

	return (
		<>
			<div className={"flex items-center gap-2"}>
				<ReleasesHelpButton />
				<Button
					variant={"outline"}
					size={"icon"}
					onClick={() => setShowIdentitiesDialog(true)}
					title={"Manage identities"}
				>
					<KeyRound className={"h-5 w-5"} />
				</Button>
				<Button
					variant={"outline"}
					size={"icon"}
					onClick={handleRemoveRepository}
					disabled={!hasRepository || isBusy}
					title={"Remove repository"}
					className={
						"text-destructive hover:text-destructive hover:bg-destructive/10"
					}
				>
					<Trash2 className={"h-5 w-5"} />
				</Button>
			</div>

			<IdentitiesManagerDialog
				open={showIdentitiesDialog}
				onOpenChange={setShowIdentitiesDialog}
			/>
		</>
	);
}
