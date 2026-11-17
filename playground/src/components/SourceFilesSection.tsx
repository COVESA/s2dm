import {
	closestCenter,
	DndContext,
	type DragEndEvent,
	KeyboardSensor,
	PointerSensor,
	useSensor,
	useSensors,
} from "@dnd-kit/core";
import {
	arrayMove,
	SortableContext,
	sortableKeyboardCoordinates,
	verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CollapsibleSection } from "@insights-ui/components/CollapsibleSection";
import { Button } from "@shared-ui/components/button";
import { Trash2 } from "lucide-react";
import { useCallback } from "react";
import { ComposeActions } from "@/components/ComposeSection";
import { useConfirmPrompt } from "@/components/ConfirmPromptProvider";
import { SourceFileEntry } from "@/components/SourceFileEntry";
import { selectHasExportResults } from "@/store/export/exportSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	selectComposedFilePaths,
	selectHasSchema,
	selectSourceFiles,
	setSourceFiles,
} from "@/store/schema/schemaSlice";
import { selectHasSelection } from "@/store/selection/selectionSlice";
import { getFileRemovalPrompt } from "@/utils/fileRemovalPrompt";

type SourceFilesSectionProps = {
	isCollapsed: boolean;
	onCollapsedChange: (isCollapsed: boolean) => void;
};

export function SourceFilesSection({
	isCollapsed,
	onCollapsedChange,
}: SourceFilesSectionProps) {
	const dispatch = useAppDispatch();
	const files = useAppSelector(selectSourceFiles);
	const hasSelection = useAppSelector(selectHasSelection);
	const hasSchema = useAppSelector(selectHasSchema);
	const hasExportResults = useAppSelector(selectHasExportResults);
	const composedFilePaths = useAppSelector(selectComposedFilePaths);
	const confirmAction = useConfirmPrompt();

	const sensors = useSensors(
		useSensor(PointerSensor),
		useSensor(KeyboardSensor, {
			coordinateGetter: sortableKeyboardCoordinates,
		}),
	);

	const handleRemove = useCallback(
		(filePath: string) => {
			const removedFile = files.find((file) => file.path === filePath);
			if (!removedFile) {
				return;
			}

			const remainingFiles = files.filter((file) => file.path !== filePath);
			const isComposed = composedFilePaths.includes(filePath);
			const hasOtherComposedFiles = remainingFiles.some((file) =>
				composedFilePaths.includes(file.path),
			);
			const removalPrompt = getFileRemovalPrompt({
				fileName: removedFile.name,
				isLastFile: remainingFiles.length === 0,
				isComposed,
				isLastComposedFile: isComposed && !hasOtherComposedFiles,
				composedItems: { hasSchema, hasSelection, hasExportResults },
			});
			const removeAction = setSourceFiles(remainingFiles);

			confirmAction({
				...removalPrompt,
				title: "Remove file?",
				confirmLabel: "Remove File",
				onConfirm: () => dispatch(removeAction),
			});
		},
		[
			composedFilePaths,
			confirmAction,
			dispatch,
			files,
			hasExportResults,
			hasSchema,
			hasSelection,
		],
	);

	const handleDragEnd = useCallback(
		(event: DragEndEvent) => {
			const { active, over } = event;
			if (!over || active.id === over.id) {
				return;
			}
			const oldIndex = files.findIndex((f) => f.path === active.id);
			const newIndex = files.findIndex((f) => f.path === over.id);
			dispatch(setSourceFiles(arrayMove(files, oldIndex, newIndex)));
		},
		[dispatch, files],
	);

	if (files.length === 0) {
		return null;
	}

	const fileCountText = `${files.length} file${files.length !== 1 ? "s" : ""}`;
	const filePaths = files.map((file) => file.path);

	const handleRemoveAll = () => {
		confirmAction({
			title: "Remove all files?",
			description: `This will remove all ${fileCountText} from the list. This action cannot be undone.`,
			confirmLabel: "Remove All",
			onConfirm: () => {
				const removeAllAction = setSourceFiles([]);
				dispatch(removeAllAction);
			},
		});
	};

	const sectionActions = (
		<div className={"flex items-center gap-1"}>
			<Button
				type={"button"}
				variant={"outline"}
				size={"icon-sm"}
				onClick={handleRemoveAll}
				title={"Remove all files"}
				className={
					"text-destructive hover:text-destructive hover:bg-destructive/10"
				}
			>
				<Trash2 />
			</Button>
			<ComposeActions />
		</div>
	);

	return (
		<CollapsibleSection
			title={fileCountText}
			className="mt-2"
			actions={sectionActions}
			isCollapsed={isCollapsed}
			onCollapsedChange={onCollapsedChange}
		>
			<div className="min-h-0 overflow-y-auto max-h-40">
				<DndContext
					sensors={sensors}
					collisionDetection={closestCenter}
					onDragEnd={handleDragEnd}
				>
					<SortableContext
						items={filePaths}
						strategy={verticalListSortingStrategy}
					>
						<ul className="space-y-1 py-2">
							{files.map((file) => (
								<SourceFileEntry
									key={file.path}
									file={file}
									onRemove={handleRemove}
								/>
							))}
						</ul>
					</SortableContext>
				</DndContext>
			</div>
		</CollapsibleSection>
	);
}
