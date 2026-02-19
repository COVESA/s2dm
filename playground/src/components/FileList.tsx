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
	useSortable,
	verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
	CheckCircle,
	FileText,
	Folder,
	GripVertical,
	Layers,
	Link,
	Plus,
	Trash2,
	Upload,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { CliCommandDisplay } from "@/components/CliCommandDisplay";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { CollapsibleSection } from "@/components/ui/collapsible-section";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dropdown, DropdownItem } from "@/components/ui/simple-dropdown";
import { resetApp } from "@/store/app/appSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectSourceFiles, setSourceFiles } from "@/store/schema/schemaSlice";
import { selectIsValidating } from "@/store/validation/validationSlice";
import { isGraphQLFile, isValidUrl } from "@/utils/validation";

export type ImportedFile = {
	name: string;
	path: string;
	type: "file" | "url";
	content?: string;
};

type FileWithPath = File & {
	webkitRelativePath?: string;
};

type FileListProps = {
	onCompose?: () => void;
};

function SortableFileItem({
	file,
	onRemove,
}: {
	file: ImportedFile;
	onRemove: (filePath: string) => void;
}) {
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

	let fileIcon: React.ReactNode;
	if (file.type === "url") {
		fileIcon = <Link className="h-4 w-4 flex-shrink-0" />;
	} else {
		fileIcon = <FileText className="h-4 w-4 flex-shrink-0" />;
	}

	return (
		<li
			ref={setNodeRef}
			style={style}
			className="group flex items-center gap-2 px-3 py-2 text-sm text-foreground bg-background/50 border border-border rounded-md hover:bg-background/80 transition-colors"
			title={file.path}
		>
			<button
				className="cursor-grab active:cursor-grabbing touch-none"
				{...attributes}
				{...listeners}
			>
				<GripVertical className="h-4 w-4 text-muted-foreground" />
			</button>
			{fileIcon}
			<span className="truncate flex-1">{file.name}</span>
			<Button
				variant="ghost"
				size="icon-sm"
				onClick={() => onRemove(file.path)}
				className="opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive hover:bg-destructive/10"
				title="Remove file"
			>
				<Trash2 />
			</Button>
		</li>
	);
}

export function FileList({ onCompose }: FileListProps) {
	const dispatch = useAppDispatch();
	const isValidating = useAppSelector(selectIsValidating);
	const files = useAppSelector(selectSourceFiles);
	const [showClearConfirm, setShowClearConfirm] = useState(false);
	const [showUrlDialog, setShowUrlDialog] = useState(false);
	const [urlInput, setUrlInput] = useState("");
	const [urlError, setUrlError] = useState("");
	const [error, setError] = useState<string>("");
	const fileInputRef = useRef<HTMLInputElement>(null);
	const folderInputRef = useRef<HTMLInputElement>(null);

	const sensors = useSensors(
		useSensor(PointerSensor),
		useSensor(KeyboardSensor, {
			coordinateGetter: sortableKeyboardCoordinates,
		}),
	);

	const handleFileChange = useCallback(
		async (event: React.ChangeEvent<HTMLInputElement>) => {
			const selectedFiles = event.target.files;
			if (!selectedFiles || selectedFiles.length === 0) return;

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

				const updatedFiles = [...files, ...fileData];
				dispatch(setSourceFiles(updatedFiles));
				setError("");
			} catch (err) {
				setError(
					`Failed to read files: ${err instanceof Error ? err.message : String(err)}`,
				);
			}

			event.target.value = "";
		},
		[files, dispatch],
	);

	const handleImportFiles = useCallback(() => {
		fileInputRef.current?.click();
	}, []);

	const handleImportFolder = useCallback(() => {
		folderInputRef.current?.click();
	}, []);

	const handleAddUrl = useCallback(() => {
		setShowUrlDialog(true);
		setUrlInput("");
		setUrlError("");
	}, []);

	const handleConfirmAddUrl = useCallback(() => {
		if (!urlInput.trim()) {
			setUrlError("URL is required");
			return;
		}

		if (!isValidUrl(urlInput)) {
			setUrlError("Please enter a valid URL");
			return;
		}

		const urlEntry: ImportedFile = {
			name: urlInput,
			path: urlInput,
			type: "url",
		};

		const updatedFiles = [...files, urlEntry];
		dispatch(setSourceFiles(updatedFiles));
		setShowUrlDialog(false);
		setUrlInput("");
		setUrlError("");
	}, [urlInput, files, dispatch]);

	const handleRemove = useCallback(
		(filePath: string) => {
			const updatedFiles = files.filter((f) => f.path !== filePath);
			dispatch(setSourceFiles(updatedFiles));
		},
		[files, dispatch],
	);

	const handleClearAll = useCallback(() => {
		setShowClearConfirm(true);
	}, []);

	const confirmClearAll = useCallback(() => {
		setShowClearConfirm(false);
		dispatch(resetApp());
	}, [dispatch]);

	const handleDragEnd = (event: DragEndEvent) => {
		const { active, over } = event;

		if (over && active.id !== over.id) {
			const oldIndex = files.findIndex((f) => f.path === active.id);
			const newIndex = files.findIndex((f) => f.path === over.id);
			const reordered = arrayMove(files, oldIndex, newIndex);
			dispatch(setSourceFiles(reordered));
		}
	};

	const renderFileList = () => {
		if (files.length === 0) {
			return null;
		}

		const fileCountText = `${files.length} file${files.length !== 1 ? "s" : ""}`;
		const filePaths = files.map((f) => f.path);
		const fileItems = files.map((file) => (
			<SortableFileItem key={file.path} file={file} onRemove={handleRemove} />
		));

		let buttonContent: React.ReactNode;
		if (isValidating) {
			buttonContent = "Validating...";
		} else if (files.length === 1) {
			buttonContent = (
				<>
					<CheckCircle />
					Validate
				</>
			);
		} else {
			buttonContent = (
				<>
					<Layers />
					Compose and Validate
				</>
			);
		}

		return (
			<CollapsibleSection title={fileCountText}>
				<div className="overflow-y-auto max-h-100">
					<DndContext
						sensors={sensors}
						collisionDetection={closestCenter}
						onDragEnd={handleDragEnd}
					>
						<SortableContext
							items={filePaths}
							strategy={verticalListSortingStrategy}
						>
							<ul className="space-y-1 py-2">{fileItems}</ul>
						</SortableContext>
					</DndContext>
				</div>
				<div className="flex gap-2">
					<Button
						variant="outline"
						size="sm"
						className="flex-1"
						onClick={onCompose}
						disabled={files.length === 0}
						loading={isValidating}
						title={
							files.length === 1
								? "Validate schema file"
								: "Compose and validate schema files"
						}
					>
						{buttonContent}
					</Button>
				</div>
			</CollapsibleSection>
		);
	};

	return (
		<div className="flex flex-col">
			<div className="flex justify-end gap-2 p-2">
				<Dropdown
					trigger={
						<Button variant="outline" size="icon" title="Add schemas">
							<Plus className="h-5 w-5" />
						</Button>
					}
					align="end"
				>
					<DropdownItem onClick={handleImportFiles}>
						<Upload className="h-4 w-4" />
						Upload Files
					</DropdownItem>
					<DropdownItem onClick={handleImportFolder}>
						<Folder className="h-4 w-4" />
						Upload Directory
					</DropdownItem>
					<DropdownItem onClick={handleAddUrl}>
						<Link className="h-4 w-4" />
						Add URL
					</DropdownItem>
				</Dropdown>
				<Button
					variant="outline"
					size="icon"
					onClick={handleClearAll}
					disabled={files.length === 0}
					title="Remove all files"
					className="text-destructive hover:text-destructive hover:bg-destructive/10"
				>
					<Trash2 className="h-5 w-5" />
				</Button>
			</div>

			{error && (
				<div className="mx-2 mb-2 p-2 text-sm bg-destructive/10 text-destructive rounded border border-destructive">
					{error}
				</div>
			)}

			{renderFileList()}

			{files.length > 0 && (
				<div className="px-2 pt-4 pb-2">
					<CliCommandDisplay type="compose" />
				</div>
			)}

			<input
				ref={fileInputRef}
				type="file"
				onChange={handleFileChange}
				style={{ display: "none" }}
				multiple
			/>

			<input
				ref={folderInputRef}
				type="file"
				onChange={handleFileChange}
				style={{ display: "none" }}
				webkitdirectory={""}
			/>

			<AlertDialog open={showClearConfirm} onOpenChange={setShowClearConfirm}>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>Remove all files?</AlertDialogTitle>
						<AlertDialogDescription>
							This will remove all {files.length} file
							{files.length !== 1 ? "s" : ""} from the list. This action cannot
							be undone.
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel>Cancel</AlertDialogCancel>
						<AlertDialogAction onClick={confirmClearAll} variant="destructive">
							Remove All
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>

			<Dialog open={showUrlDialog} onOpenChange={setShowUrlDialog}>
				<DialogContent>
					<DialogHeader>
						<DialogTitle>Add Schema URL</DialogTitle>
						<DialogDescription>
							Enter the URL of a GraphQL schema to add to your file list.
						</DialogDescription>
					</DialogHeader>
					<div className="grid gap-4 py-4">
						<div className="grid gap-2">
							<Label htmlFor="schema-url">Schema URL</Label>
							<Input
								id="schema-url"
								placeholder="https://example.com/schema.graphql"
								value={urlInput}
								onChange={(e) => {
									setUrlInput(e.target.value);
									setUrlError("");
								}}
								onKeyDown={(e) => {
									if (e.key === "Enter") {
										handleConfirmAddUrl();
									}
								}}
							/>
							{urlError && (
								<p className="text-sm text-destructive">{urlError}</p>
							)}
						</div>
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setShowUrlDialog(false)}>
							Cancel
						</Button>
						<Button onClick={handleConfirmAddUrl}>Add URL</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}
