import { Plus, Upload } from "lucide-react";
import { useCallback } from "react";
import { DependencyModal } from "@/components/DependencyModal";
import { BuiltSchemaViewerButton } from "@/components/dependencies/BuiltSchemaViewerButton";
import { DependencyImportDialog } from "@/components/dependencies/DependencyImportDialog";
import { EntryList } from "@/components/dependencies/EntryList";
import { useEditModal } from "@/components/dependencies/useEditModal";
import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import { SplitActionButton } from "@/components/ui/split-action-button";
import { StatusBanner } from "@/components/ui/status-banner";
import { TabsContent } from "@/components/ui/tabs";
import { useDependencyConfigImportController } from "@/hooks/useDependencyConfigImportController";
import {
	composeDependencies,
	selectComposeError,
	selectComposeMessage,
	selectIsComposing,
} from "@/store/deps/compose/composeSlice";
import {
	addDependency,
	removeDependency,
	saveDependenciesConfig,
	selectDependenciesError,
	selectDependencyDrafts,
	selectDependencyStatus,
	selectHasUnsavedDependencyChanges,
	selectIsImportingDependenciesConfig,
	selectIsLoadingDependenciesConfig,
	selectIsLoadingDependencyStatus,
	selectIsSavingDependenciesConfig,
	updateDependency,
} from "@/store/deps/depsSlice";
import { selectIsSavingIdentities } from "@/store/deps/identities/identitiesSlice";
import {
	resolveDependencies,
	selectIsResolvingDependencies,
	selectResolveError,
	selectResolveWarnings,
} from "@/store/deps/resolve/resolveSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	createEmptyDependencyDraft,
	type DependencyDraft,
} from "@/types/dependency";

type DependenciesTabProps = {
	onDialogClose: () => void;
};

function getDependencySummary(dependency: DependencyDraft) {
	return {
		primary: dependency.name.trim() || "New dependency",
		secondary: dependency.version.trim(),
	};
}

export function DependenciesTab({ onDialogClose }: DependenciesTabProps) {
	const dispatch = useAppDispatch();
	const depModal = useEditModal<DependencyDraft>();
	const {
		fileImport,
		pendingImport,
		configDirectory,
		configDirectoryError,
		handleConfigDirectoryChange,
		handleConfirmImport,
		closeImportDialog,
	} = useDependencyConfigImportController();

	const dependencies = useAppSelector(selectDependencyDrafts);
	const dependenciesError = useAppSelector(selectDependenciesError);
	const resolveError = useAppSelector(selectResolveError);
	const dependencyWarnings = useAppSelector(selectResolveWarnings);
	const dependenciesComposeMessage = useAppSelector(selectComposeMessage);
	const dependenciesComposeError = useAppSelector(selectComposeError);
	const isDependenciesLoading = useAppSelector(
		selectIsLoadingDependenciesConfig,
	);
	const isDependenciesImporting = useAppSelector(
		selectIsImportingDependenciesConfig,
	);
	const isDependenciesSaving = useAppSelector(selectIsSavingDependenciesConfig);
	const isDependenciesResolving = useAppSelector(selectIsResolvingDependencies);
	const isDependenciesComposing = useAppSelector(selectIsComposing);
	const isIdentitiesSaving = useAppSelector(selectIsSavingIdentities);
	const dependencyStatus = useAppSelector(selectDependencyStatus);
	const isDependencyStatusLoading = useAppSelector(
		selectIsLoadingDependencyStatus,
	);
	const hasUnsavedDependencyChanges = useAppSelector(
		selectHasUnsavedDependencyChanges,
	);

	const handleOpenAdd = useCallback(() => {
		depModal.openAdd(createEmptyDependencyDraft());
	}, [depModal]);

	const handleCloseModal = useCallback(
		(isOpen: boolean) => {
			if (!isOpen) {
				depModal.close();
			}
		},
		[depModal],
	);

	const handleSaveDraft = useCallback(
		(dependency: DependencyDraft) => {
			if (depModal.mode === "add") {
				dispatch(addDependency(dependency));
			} else {
				dispatch(updateDependency(dependency));
			}

			depModal.close();
		},
		[depModal, dispatch],
	);

	const handleSave = useCallback(() => {
		dispatch(saveDependenciesConfig());
	}, [dispatch]);

	const handleResolve = useCallback(() => {
		dispatch(resolveDependencies({ clean: false }));
	}, [dispatch]);

	const handleCleanResolve = useCallback(() => {
		dispatch(resolveDependencies({ clean: true }));
	}, [dispatch]);

	const handleCompose = useCallback(() => {
		dispatch(composeDependencies({ autoPrefix: false }));
	}, [dispatch]);

	const handleComposeWithAutoPrefix = useCallback(() => {
		dispatch(composeDependencies({ autoPrefix: true }));
	}, [dispatch]);

	const isAnySaveInProgress =
		isDependenciesImporting || isDependenciesSaving || isIdentitiesSaving;
	const isAddDisabled =
		isDependenciesLoading ||
		isAnySaveInProgress ||
		isDependenciesResolving ||
		isDependenciesComposing;
	const isResolveDisabled =
		isDependencyStatusLoading ||
		isDependenciesSaving ||
		isDependenciesComposing ||
		isDependenciesResolving;
	const isComposeDisabled =
		dependencyStatus !== "resolved" ||
		isDependencyStatusLoading ||
		isDependenciesSaving ||
		isIdentitiesSaving ||
		isDependenciesResolving ||
		isDependenciesComposing;
	const isSaveDisabled =
		isDependenciesLoading ||
		isAnySaveInProgress ||
		isDependenciesResolving ||
		isDependenciesComposing ||
		!hasUnsavedDependencyChanges;
	const destructiveErrorMessages = [
		dependenciesError,
		resolveError,
		dependenciesComposeError,
	];
	const destructiveErrors = destructiveErrorMessages.filter(
		(error): error is string => Boolean(error),
	);
	const uniqueDestructiveErrors = Array.from(new Set(destructiveErrors));

	return (
		<>
			<TabsContent
				value="dependencies"
				className="mt-0 flex min-h-0 flex-1 flex-col"
			>
				<div className="flex justify-end gap-2 pr-1 pt-2">
					<BuiltSchemaViewerButton size="icon-sm" />
					<Button
						variant="outline"
						size="icon-sm"
						onClick={fileImport.openImportInput}
						loading={isDependenciesImporting}
						disabled={isAddDisabled}
						title="Import dependencies config"
					>
						<Upload />
					</Button>
					<Button
						variant="outline"
						size="icon-sm"
						onClick={handleOpenAdd}
						disabled={isAddDisabled}
						title="Add dependency"
					>
						<Plus />
					</Button>
				</div>

				<div className="px-1">
					{uniqueDestructiveErrors.map((error) => (
						<StatusBanner key={error} variant="destructive" className="mt-2">
							{error}
						</StatusBanner>
					))}

					{dependencyWarnings.length > 0 && (
						<StatusBanner variant="warning" className="mt-2">
							{dependencyWarnings.join("\n")}
						</StatusBanner>
					)}

					{dependenciesComposeMessage && (
						<StatusBanner variant="success" className="mt-2">
							{dependenciesComposeMessage}
						</StatusBanner>
					)}
				</div>
				<EntryList
					items={dependencies}
					isLoading={isDependenciesLoading}
					loadingTitle="Loading dependencies..."
					emptyTitle="No dependencies configured"
					getSummary={getDependencySummary}
					onEdit={(dependency) => depModal.openEdit(dependency)}
					onRemove={(dependency) => {
						dispatch(removeDependency(dependency.id));
						depModal.closeIfMatches(dependency.id);
					}}
					removeTitle="Remove dependency"
				/>

				<DialogFooter className="mt-6">
					<Button
						variant="outline"
						onClick={onDialogClose}
						disabled={isAnySaveInProgress}
					>
						Cancel
					</Button>
					<SplitActionButton
						label="Resolve"
						onClick={handleResolve}
						loading={isDependenciesResolving}
						disabled={isResolveDisabled}
						title="Resolve dependencies"
						optionsTitle="Resolve options"
						options={[
							{ label: "Clean and Resolve", onClick: handleCleanResolve },
						]}
					/>
					<SplitActionButton
						label="Build"
						onClick={handleCompose}
						loading={isDependenciesComposing}
						disabled={isComposeDisabled}
						title="Build dependencies"
						optionsTitle="Build options"
						options={[
							{
								label: "Build and Auto-prefix",
								onClick: handleComposeWithAutoPrefix,
							},
						]}
					/>
					<Button
						onClick={handleSave}
						loading={isDependenciesSaving}
						disabled={isSaveDisabled}
					>
						Save
					</Button>
				</DialogFooter>
			</TabsContent>

			{depModal.isOpen && depModal.draft && depModal.mode && (
				<DependencyModal
					open={depModal.isOpen}
					mode={depModal.mode}
					dependency={depModal.draft}
					onOpenChange={handleCloseModal}
					onSave={handleSaveDraft}
				/>
			)}

			<input {...fileImport.hiddenInputProps} />

			<DependencyImportDialog
				open={pendingImport !== null}
				filename={pendingImport?.filename ?? ""}
				configDirectory={configDirectory}
				error={configDirectoryError}
				onConfigDirectoryChange={handleConfigDirectoryChange}
				onConfirm={handleConfirmImport}
				onOpenChange={(isOpen) => {
					if (!isOpen) {
						closeImportDialog();
					}
				}}
			/>
		</>
	);
}
