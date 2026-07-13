import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { FileText, GripVertical, Link, Trash2 } from "lucide-react";
import { FileListRow } from "@/components/FileListRow";
import { Button } from "@/components/ui/button";
import type { ImportedFile } from "@/types/importedFile";

type SourceFileEntryProps = {
	file: ImportedFile;
	onRemove: (filePath: string) => void;
};

export function SourceFileEntry({ file, onRemove }: SourceFileEntryProps) {
	const {
		attributes,
		listeners,
		setNodeRef,
		transform,
		transition,
		isDragging,
	} = useSortable({ id: file.path });

	const style = {
		transform: CSS.Transform.toString(transform),
		transition,
		opacity: isDragging ? 0.5 : 1,
	};

	let icon = <FileText className="h-4 w-4 flex-shrink-0" />;
	if (file.type === "url") {
		icon = <Link className="h-4 w-4 flex-shrink-0" />;
	}

	const reorderLabel = `Reorder ${file.name}`;
	const removeLabel = `Remove ${file.name}`;

	return (
		<FileListRow
			ref={setNodeRef}
			style={style}
			title={file.path}
			label={file.name}
			leading={
				<button
					type="button"
					className="cursor-grab touch-none active:cursor-grabbing"
					aria-label={reorderLabel}
					title={reorderLabel}
					{...attributes}
					{...listeners}
				>
					<GripVertical className="h-4 w-4 text-muted-foreground" />
				</button>
			}
			icon={icon}
			trailing={
				<Button
					type="button"
					variant="ghost"
					size="icon-sm"
					onClick={() => onRemove(file.path)}
					className="text-destructive opacity-0 transition-opacity group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive"
					aria-label={removeLabel}
					title={removeLabel}
				>
					<Trash2 />
				</Button>
			}
		/>
	);
}
