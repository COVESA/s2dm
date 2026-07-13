import { type ReactNode, useCallback, useState } from "react";
import { useFileImport } from "@/hooks/useFileImport";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectSourceFiles, setSourceFiles } from "@/store/schema/schemaSlice";
import type { ImportedFile } from "@/types/importedFile";
import { getErrorMessage } from "@/utils/getErrorMessage";
import { isGraphQLFile } from "@/utils/validation";

type FileWithPath = File & {
	webkitRelativePath?: string;
};

export function useImportSources() {
	const dispatch = useAppDispatch();
	const files = useAppSelector(selectSourceFiles);
	const [error, setError] = useState("");

	const handleImportedFiles = useCallback(
		async (selectedFiles: FileList) => {
			const graphqlFiles: File[] = [];
			for (let i = 0; i < selectedFiles.length; i++) {
				const file = selectedFiles[i];
				if (isGraphQLFile(file.name)) {
					graphqlFiles.push(file);
				}
			}

			if (graphqlFiles.length === 0) {
				setError(
					"No GraphQL files found. Please select files with .graphql or .gql extensions.",
				);
				return;
			}

			try {
				const fileData = await Promise.all(
					graphqlFiles.map(async (file) => {
						const fileWithPath = file as FileWithPath;
						return {
							name: file.name,
							path: fileWithPath.webkitRelativePath || file.name,
							content: await file.text(),
							type: "file" as const,
						};
					}),
				);
				dispatch(setSourceFiles([...files, ...fileData]));
				setError("");
			} catch (err) {
				setError(`Failed to read files: ${getErrorMessage(err)}`);
			}
		},
		[files, dispatch],
	);

	const fileImport = useFileImport({
		accept: ".graphql,.gql",
		multiple: true,
		onFilesSelected: handleImportedFiles,
	});

	const folderImport = useFileImport({
		directory: true,
		multiple: true,
		onFilesSelected: handleImportedFiles,
	});

	const addUrl = useCallback(
		(url: string) => {
			const urlEntry: ImportedFile = {
				name: url,
				path: url,
				type: "url",
			};
			dispatch(setSourceFiles([...files, urlEntry]));
		},
		[files, dispatch],
	);

	const hiddenInputs: ReactNode = (
		<>
			<input {...fileImport.hiddenInputProps} />
			<input {...folderImport.hiddenInputProps} />
		</>
	);

	return {
		openFileImport: fileImport.openImportInput,
		openFolderImport: folderImport.openImportInput,
		addUrl,
		error,
		hiddenInputs,
	};
}
