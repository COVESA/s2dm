import { useEffect } from "react";
import { useConfirmPrompt } from "@/components/ConfirmPromptProvider";
import { IdentitiesManager } from "@/components/dependencies/IdentitiesManager";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import {
	discardIdentityChanges,
	fetchIdentities,
	selectHasUnsavedIdentityChanges,
} from "@/store/deps/identities/identitiesSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";

type IdentitiesManagerDialogProps = {
	open: boolean;
	onOpenChange: (open: boolean) => void;
};

export function IdentitiesManagerDialog({
	open,
	onOpenChange,
}: IdentitiesManagerDialogProps) {
	const dispatch = useAppDispatch();
	const hasUnsavedIdentityChanges = useAppSelector(
		selectHasUnsavedIdentityChanges,
	);
	const confirmAction = useConfirmPrompt();

	useEffect(() => {
		if (!open) {
			return;
		}

		const fetchAction = fetchIdentities();
		dispatch(fetchAction);
	}, [dispatch, open]);

	const handleOpenChange = (isOpen: boolean) => {
		if (isOpen) {
			onOpenChange(true);
			return;
		}

		confirmAction({
			isDataLost: hasUnsavedIdentityChanges,
			description: "The unsaved identity changes will be lost.",
			onConfirm: () => {
				const discardAction = discardIdentityChanges();
				dispatch(discardAction);
				onOpenChange(false);
			},
		});
	};

	return (
		<Dialog open={open} onOpenChange={handleOpenChange}>
			<DialogContent className="flex h-[50vh] w-[90vw] max-w-4xl flex-col sm:max-w-4xl">
				<DialogHeader>
					<DialogTitle>Manage Identities</DialogTitle>
				</DialogHeader>
				<IdentitiesManager onClose={() => handleOpenChange(false)} />
			</DialogContent>
		</Dialog>
	);
}
