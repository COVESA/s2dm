import { useCallback, useMemo, useState } from "react";

export type EditModalMode = "add" | "edit";

export type UseEditModalResult<T extends { id: string }> = {
	mode: EditModalMode | null;
	draft: T | null;
	isOpen: boolean;
	openAdd: (empty: T) => void;
	openEdit: (entry: T) => void;
	close: () => void;
	closeIfMatches: (id: string) => void;
};

export function useEditModal<
	T extends { id: string },
>(): UseEditModalResult<T> {
	const [mode, setMode] = useState<EditModalMode | null>(null);
	const [draft, setDraft] = useState<T | null>(null);

	const openAdd = useCallback((empty: T) => {
		setMode("add");
		setDraft(empty);
	}, []);

	const openEdit = useCallback((entry: T) => {
		setMode("edit");
		setDraft({ ...entry });
	}, []);

	const close = useCallback(() => {
		setMode(null);
		setDraft(null);
	}, []);

	const closeIfMatches = useCallback(
		(id: string) => {
			if (draft?.id === id) {
				setMode(null);
				setDraft(null);
			}
		},
		[draft?.id],
	);

	return useMemo(
		() => ({
			mode,
			draft,
			isOpen: mode !== null && draft !== null,
			openAdd,
			openEdit,
			close,
			closeIfMatches,
		}),
		[mode, draft, openAdd, openEdit, close, closeIfMatches],
	);
}
