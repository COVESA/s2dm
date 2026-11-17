import { Button } from "@shared-ui/components/button";
import { StatusBanner } from "@shared-ui/components/status-banner";
import { Plus, Upload } from "lucide-react";
import { useCallback } from "react";
import { DependencyIdentityModal } from "@/components/DependencyIdentityModal";
import { EntryList } from "@/components/dependencies/EntryList";
import { useEditModal } from "@/components/dependencies/useEditModal";
import { DialogFooter } from "@/components/ui/dialog";
import { useFileImport } from "@/hooks/useFileImport";
import { selectIsSavingDependenciesConfig } from "@/store/deps/depsSlice";
import { parseDependenciesIdentitiesYaml } from "@/store/deps/identities/identitiesMappers";
import {
	addIdentity,
	importIdentitiesFile,
	importIdentitiesFileFailure,
	removeIdentity,
	saveIdentities,
	selectHasUnsavedIdentityChanges,
	selectIdentitiesError,
	selectIdentityDrafts,
	selectIsImportingIdentities,
	selectIsLoadingIdentities,
	selectIsSavingIdentities,
	updateIdentity,
} from "@/store/deps/identities/identitiesSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	createEmptyDependencyIdentityDraft,
	type DependencyIdentityDraft,
} from "@/types/dependencyIdentity";
import { getErrorMessage } from "@/utils/getErrorMessage";

type IdentitiesManagerProps = {
	onClose: () => void;
};

function getIdentitySummary(identity: DependencyIdentityDraft) {
	return {
		primary: identity.host.trim() || "New identity",
		secondary: identity.scope.trim(),
	};
}

/**
 * Lists the stored identities and lets the user import, add, edit, remove and
 * save them.
 *
 * @param onClose Called when the user clicks Cancel.
 * @returns The identities manager.
 */
export function IdentitiesManager({ onClose }: IdentitiesManagerProps) {
	const dispatch = useAppDispatch();
	const idModal = useEditModal<DependencyIdentityDraft>();

	const identities = useAppSelector(selectIdentityDrafts);
	const identitiesError = useAppSelector(selectIdentitiesError);
	const isIdentitiesImporting = useAppSelector(selectIsImportingIdentities);
	const isIdentitiesLoading = useAppSelector(selectIsLoadingIdentities);
	const isIdentitiesSaving = useAppSelector(selectIsSavingIdentities);
	const isDependenciesSaving = useAppSelector(selectIsSavingDependenciesConfig);
	const hasUnsavedIdentityChanges = useAppSelector(
		selectHasUnsavedIdentityChanges,
	);

	const handleOpenAdd = useCallback(() => {
		idModal.openAdd(createEmptyDependencyIdentityDraft());
	}, [idModal]);

	const handleCloseModal = useCallback(
		(isOpen: boolean) => {
			if (!isOpen) {
				idModal.close();
			}
		},
		[idModal],
	);

	const handleSaveDraft = useCallback(
		(identity: DependencyIdentityDraft) => {
			if (idModal.mode === "add") {
				dispatch(addIdentity(identity));
			} else {
				dispatch(updateIdentity(identity));
			}

			idModal.close();
		},
		[dispatch, idModal],
	);

	const handleSave = useCallback(() => {
		dispatch(saveIdentities());
	}, [dispatch]);

	const { openImportInput, hiddenInputProps } = useFileImport({
		accept: ".yaml,.yml",
		onFilesSelected: async (selectedFiles) => {
			const selectedFile = selectedFiles[0];
			if (!selectedFile) {
				return;
			}

			try {
				const fileContent = await selectedFile.text();
				const identities = parseDependenciesIdentitiesYaml(fileContent);
				dispatch(importIdentitiesFile(identities));
			} catch (importError) {
				dispatch(importIdentitiesFileFailure(getErrorMessage(importError)));
			}
		},
	});

	const isAnySaveInProgress =
		isDependenciesSaving || isIdentitiesImporting || isIdentitiesSaving;
	const isAddDisabled = isIdentitiesLoading || isAnySaveInProgress;
	const isSaveDisabled =
		isIdentitiesLoading || isAnySaveInProgress || !hasUnsavedIdentityChanges;

	return (
		<>
			<div className="flex justify-end gap-2 pr-1">
				<Button
					variant="outline"
					size="icon-sm"
					onClick={openImportInput}
					loading={isIdentitiesImporting}
					disabled={isAddDisabled}
					title="Import identities config"
				>
					<Upload />
				</Button>
				<Button
					variant="outline"
					size="icon-sm"
					onClick={handleOpenAdd}
					disabled={isAddDisabled}
					title="Add identity"
				>
					<Plus />
				</Button>
			</div>

			{identitiesError && (
				<StatusBanner variant={"destructive"}>{identitiesError}</StatusBanner>
			)}

			<EntryList
				items={identities}
				isLoading={isIdentitiesLoading}
				loadingTitle="Loading identities..."
				emptyTitle="No identities configured"
				getSummary={getIdentitySummary}
				onEdit={(identity) => idModal.openEdit(identity)}
				onRemove={(identity) => {
					dispatch(removeIdentity(identity.id));
					idModal.closeIfMatches(identity.id);
				}}
				removeTitle="Remove identity"
			/>

			<DialogFooter>
				<Button
					variant="outline"
					onClick={onClose}
					disabled={isAnySaveInProgress}
				>
					Cancel
				</Button>
				<Button
					onClick={handleSave}
					loading={isIdentitiesSaving}
					disabled={isSaveDisabled}
				>
					Save
				</Button>
			</DialogFooter>

			{idModal.isOpen && idModal.draft && idModal.mode && (
				<DependencyIdentityModal
					open={idModal.isOpen}
					mode={idModal.mode}
					identity={idModal.draft}
					onOpenChange={handleCloseModal}
					onSave={handleSaveDraft}
				/>
			)}

			<input {...hiddenInputProps} />
		</>
	);
}
