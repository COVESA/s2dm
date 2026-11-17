import { IdentitiesManager } from "@/components/dependencies/IdentitiesManager";
import { DialogTabsContent } from "@/components/ui/dialog";

type IdentitiesTabProps = {
	onDialogClose: () => void;
};

export function IdentitiesTab({ onDialogClose }: IdentitiesTabProps) {
	return (
		<DialogTabsContent value={"identities"}>
			<IdentitiesManager onClose={onDialogClose} />
		</DialogTabsContent>
	);
}
