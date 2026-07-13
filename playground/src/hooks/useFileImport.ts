import { useCallback, useMemo, useRef } from "react";

type UseFileImportOptions = {
	accept?: string;
	directory?: boolean;
	multiple?: boolean;
	onFilesSelected: (selectedFiles: FileList) => void | Promise<void>;
};

export function useFileImport({
	accept,
	directory = false,
	multiple = false,
	onFilesSelected,
}: UseFileImportOptions) {
	const inputRef = useRef<HTMLInputElement>(null);

	const openImportInput = useCallback(() => {
		inputRef.current?.click();
	}, []);

	const handleImportInputChange = useCallback(
		(event: React.ChangeEvent<HTMLInputElement>) => {
			const selectedFiles = event.target.files;
			if (!selectedFiles || selectedFiles.length === 0) {
				return;
			}

			onFilesSelected(selectedFiles);
			event.target.value = "";
		},
		[onFilesSelected],
	);

	const hiddenInputProps = useMemo(
		() => ({
			ref: inputRef,
			type: "file" as const,
			accept,
			multiple,
			onChange: handleImportInputChange,
			style: { display: "none" },
			...(directory ? { webkitdirectory: "" } : {}),
		}),
		[accept, directory, multiple, handleImportInputChange],
	);

	return { openImportInput, hiddenInputProps };
}
