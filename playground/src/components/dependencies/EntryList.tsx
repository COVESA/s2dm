import { EntryRow } from "@/components/dependencies/EntryRow";
import { EmptyState } from "@/components/ui/empty-state";

type EntrySummary = {
	primary: string;
	secondary?: string;
};

type EntryListProps<T extends { id: string }> = {
	items: T[];
	isLoading: boolean;
	loadingTitle: string;
	emptyTitle: string;
	getSummary: (item: T) => EntrySummary;
	onEdit: (item: T) => void;
	onRemove: (item: T) => void;
	removeTitle: string;
};

export function EntryList<T extends { id: string }>({
	items,
	isLoading,
	loadingTitle,
	emptyTitle,
	getSummary,
	onEdit,
	onRemove,
	removeTitle,
}: EntryListProps<T>) {
	let content: React.ReactNode;
	if (isLoading) {
		content = <EmptyState isLoading title={loadingTitle} />;
	} else if (items.length === 0) {
		content = (
			<EmptyState
				title={emptyTitle}
				className="min-h-48 items-center justify-center rounded-md border border-dashed"
			/>
		);
	} else {
		content = (
			<div className="space-y-3">
				{items.map((item) => {
					const summary = getSummary(item);
					return (
						<EntryRow
							key={item.id}
							primary={summary.primary}
							secondary={summary.secondary}
							onEdit={() => onEdit(item)}
							onRemove={() => onRemove(item)}
							removeTitle={removeTitle}
						/>
					);
				})}
			</div>
		);
	}

	return (
		<div className="min-h-0 flex-1 overflow-y-auto pr-1 pt-4">{content}</div>
	);
}
