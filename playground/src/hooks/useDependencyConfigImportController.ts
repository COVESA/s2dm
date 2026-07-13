import { isAbsolute } from "pathe";
import { useCallback, useState } from "react";
import type { DependenciesConfig } from "@/api/types";
import { useFileImport } from "@/hooks/useFileImport";
import {
	hasRelativeDependencySelectionPaths,
	parseDependenciesConfigYaml,
} from "@/store/deps/depsMappers";
import {
	clearDependenciesError,
	importDependenciesConfig,
	importDependenciesConfigFailure,
} from "@/store/deps/depsSlice";
import { useAppDispatch } from "@/store/hooks";
import { getErrorMessage } from "@/utils/getErrorMessage";

type PendingDependencyImport = {
	config: DependenciesConfig;
	filename: string;
};

export function useDependencyConfigImportController() {
	const dispatch = useAppDispatch();
	const [pendingImport, setPendingImport] =
		useState<PendingDependencyImport | null>(null);
	const [configDirectory, setConfigDirectory] = useState("");
	const [configDirectoryError, setConfigDirectoryError] = useState("");

	const closeImportDialog = useCallback(() => {
		setPendingImport(null);
		setConfigDirectory("");
		setConfigDirectoryError("");
	}, []);

	const handleConfigDirectoryChange = useCallback((value: string) => {
		setConfigDirectory(value);
		setConfigDirectoryError("");
	}, []);

	const handleConfirmImport = useCallback(() => {
		if (pendingImport === null) {
			return;
		}

		const trimmedConfigDirectory = configDirectory.trim();
		if (!trimmedConfigDirectory) {
			setConfigDirectoryError("Config directory is required.");
			return;
		}
		if (!isAbsolute(trimmedConfigDirectory)) {
			setConfigDirectoryError("Config directory must be an absolute path.");
			return;
		}

		dispatch(
			importDependenciesConfig({
				...pendingImport.config,
				config_directory: trimmedConfigDirectory,
			}),
		);
		closeImportDialog();
	}, [closeImportDialog, configDirectory, dispatch, pendingImport]);

	const fileImport = useFileImport({
		accept: ".yaml,.yml",
		onFilesSelected: async (selectedFiles) => {
			const selectedFile = selectedFiles[0];
			if (!selectedFile) {
				return;
			}

			dispatch(clearDependenciesError());

			try {
				const fileContent = await selectedFile.text();
				const config = parseDependenciesConfigYaml(fileContent);

				if (hasRelativeDependencySelectionPaths(config)) {
					setPendingImport({ config, filename: selectedFile.name });
					setConfigDirectory("");
					setConfigDirectoryError("");
					return;
				}

				dispatch(importDependenciesConfig(config));
			} catch (importError) {
				dispatch(importDependenciesConfigFailure(getErrorMessage(importError)));
			}
		},
	});

	return {
		fileImport,
		pendingImport,
		configDirectory,
		configDirectoryError,
		handleConfigDirectoryChange,
		handleConfirmImport,
		closeImportDialog,
	};
}
