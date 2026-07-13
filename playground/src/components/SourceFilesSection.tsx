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
import { useCallback } from "react";
import { SourceFileEntry } from "@/components/SourceFileEntry";
import { CollapsibleSection } from "@/components/ui/collapsible-section";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectSourceFiles, setSourceFiles } from "@/store/schema/schemaSlice";

export function SourceFilesSection() {
	const dispatch = useAppDispatch();
	const files = useAppSelector(selectSourceFiles);

	const sensors = useSensors(
		useSensor(PointerSensor),
		useSensor(KeyboardSensor, {
			coordinateGetter: sortableKeyboardCoordinates,
		}),
	);

	const handleRemove = useCallback(
		(filePath: string) => {
			dispatch(setSourceFiles(files.filter((f) => f.path !== filePath)));
		},
		[dispatch, files],
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

	return (
		<CollapsibleSection title={fileCountText} className="mt-2">
			<div className="overflow-y-auto max-h-80">
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
